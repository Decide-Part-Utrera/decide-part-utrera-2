from django.db.utils import IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_201_CREATED as ST_201,
    HTTP_204_NO_CONTENT as ST_204,
    HTTP_400_BAD_REQUEST as ST_400,
    HTTP_401_UNAUTHORIZED as ST_401,
    HTTP_409_CONFLICT as ST_409
)

from django.utils.datastructures import MultiValueDictKeyError
from ldap3.core.exceptions import LDAPBindError
from tablib import Dataset
from base.perms import UserIsStaff
from .models import Census
from django.contrib.auth.decorators import login_required
from .resources import CensusResource
from django.contrib import messages
from django.shortcuts import render, redirect
from .ldapFunctions import LdapCensus
from census.forms import *
from voting.models import Voting
from django.contrib.auth.models import User



class CensusCreate(generics.ListCreateAPIView):
    permission_classes = (UserIsStaff,)

    def create(self, request, *args, **kwargs):
        voting_id = request.data.get('voting_id')
        voters = request.data.get('voters')
        try:
            for voter in voters:
                census = Census(voting_id=voting_id, voter_id=voter)
                census.save()
        except IntegrityError:
            return Response('Error try to create census', status=ST_409)
        return Response('Census created', status=ST_201)

    def list(self, request, *args, **kwargs):
        voting_id = request.GET.get('voting_id')
        voters = Census.objects.filter(
            voting_id=voting_id).values_list('voter_id', flat=True)
        return Response({'voters': voters})


class CensusDetail(generics.RetrieveDestroyAPIView):

    def destroy(self, request, voting_id, *args, **kwargs):
        voters = request.data.get('voters')
        census = Census.objects.filter(
            voting_id=voting_id, voter_id__in=voters)
        census.delete()
        return Response('Voters deleted from census', status=ST_204)

    def retrieve(self, request, voting_id, *args, **kwargs):
        voter = request.GET.get('voter_id')
        try:
            Census.objects.get(voting_id=voting_id, voter_id=voter)
        except ObjectDoesNotExist:
            return Response('Invalid voter', status=ST_401)
        return Response('Valid voter')


def censusShow(request):
    context = {
        'allCensus': Census.objects.all(),
    }
    return render(request, "showAllCensus.html", context)


def censusShowDetails(request, id):
    context = {
        'census': Census.objects.get(id=id)
    }
    return render(request, "census_detail.html", context)


def votersInVoting(request, voting_id):
    censusByVoting = Census.objects.filter(voting_id=voting_id)
    voters = []
    for census in censusByVoting:
        voter = User.objects.get(id=census.voter_id)
        voters.append(voter)
    context = {
        'voters': voters,
        'voting_id': voting_id
    }
    return render(request, "votersInVoting.html", context)


def showVotings(request):
    votings = Voting.objects.all()
    context = {
        'votings': votings
    }
    return render(request, "showAllVotings.html", context)


def createCensus(request, voting_id):
    if request.method == 'POST':
        if request.user.is_staff:
            form = CensusCreateForm(request.POST)
            if form.is_valid():
                voter = form.cleaned_data['voters']
                census = Census(voting_id=voting_id, voter_id=voter.id)
                try:
                    census.save()
                except IntegrityError:
                    messages.add_message(
                        request, messages.ERROR, "El usuario no se ha añadido ya que estaba en la base de datos")
        else:
            messages.add_message(
                        request, messages.ERROR, "El usuario no tiene permisos de administrador")
        return redirect('/census/voting/%s' % (voting_id))
    else:
        form = CensusCreateForm()
        context = {
            'voting_id': voting_id,
            'form': form
        }
        return render(request, "createCensus.html", context)

def deleteCensus(request, voting_id, voter_id):
    if request.user.is_staff:
        census = Census.objects.get(voting_id = voting_id, voter_id = voter_id)
        try:
            census.delete()
        except IntegrityError:
            messages.add_message(
                        request, messages.ERROR, "No se ha podido eliminar al votante")
    else:
        messages.add_message(
                        request, messages.ERROR, "El usuario no tiene permisos de administrador")
    return redirect('/census/voting/%s' % (voting_id))

def importCensusFromLdapVotacion(request):
    """This method processes the parameters sent by the form to call the connection method and the import LDAP method
    to be able to create the census containing the users from the LDAP branch previously especified. This will work
    if the users are already registered on the system.  
        
    Args:
        request: contains the HTTP data of the LDAP import
        """ 
    if request.user.is_staff:

        if request.method == 'POST':
            form = CensusAddLdapFormVotacion(request.POST)

            if form.is_valid():
                urlLdap = form.cleaned_data['urlLdap']
                treeSufix = form.cleaned_data['treeSufix']
                pwd = form.cleaned_data['pwd']
                branch = form.cleaned_data['branch']
                voting = form.cleaned_data['voting'].__getattribute__('pk')

                voters = User.objects.all()
                try:
                    usernameList = LdapCensus().ldapGroups(urlLdap, treeSufix, pwd, branch)
                    userList = []
                    for username in usernameList:
                        user = voters.filter(username=username)
                        if user:
                            user = user.values('id')[0]['id']
                            userList.append(user)
                except LDAPBindError:
                    messages.add_message(request, messages.ERROR, "Los datos del formulario son erróneos")            
                    return redirect('/census/voting')

            if request.user.is_authenticated:
                for username in userList:
                    census = Census(voting_id=voting, voter_id=username)
                    census_list = Census.objects.all()
                    voter = User.objects.all().filter(id=username)[0]
                    voter_name = voter.username
                    
                    try:
                        census.save()
                    except IntegrityError:
                        messages.add_message(request, messages.ERROR, "El usuario " + voter_name + " ya se encuentra en la base de datos")
                    
            return redirect('/census/voting')
        else:
            form = CensusAddLdapFormVotacion()

        context = {
            'form': form,
        }
        return render(request, template_name='importarCensusLdapVotacion.html', context=context)
    else:
        messages.add_message(request, messages.ERROR, "permiso denegado")
        return redirect('/admin')



#Este método sirve para exportar desde excel
def importar(request):
    if request.user.is_staff:
        if request.method == 'POST':
            census_resource = CensusResource()
            dataset = Dataset()
            try:
                nuevos_censos = request.FILES['xlsfile']
            except MultiValueDictKeyError:
                messages.add_message(request, messages.ERROR, "No has enviado nada")
                return redirect('/census/voting')
            dataset.load(nuevos_censos.read())
            validate=validate_dataset(dataset)
            if(validate):
                census_resource.import_data(dataset, dry_run=False)
                return redirect('/census/voting')
            else:
                messages.add_message(request, messages.ERROR, "El formato del archivo excel no es el correcto")
                return redirect('/census/voting')
        return render(request, 'importarExcel.html')
    else:
        messages.add_message(request, messages.ERROR, "permiso denegado")
        return redirect('/admin')

# Función para validar los que todos los campos del fichero .xlsx son correctos
def validate_dataset(dataset):
    if(dataset.headers==['voting_id', 'voter_id']):
        votaciones = Voting.objects.all()
        voters = User.objects.all()
        for row in dataset:
            votante_filtrado = voters.filter(id=row[1])
            votacion_filtrada = votaciones.filter(id=row[0])
            if(len(votacion_filtrada) == 0 or len(votante_filtrado) == 0):
                return False
        return True   
    else:
        return False
            
