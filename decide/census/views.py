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
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from .forms import UserRegisterForm
from .resources import CensusResource
from django.contrib import messages
from django.shortcuts import render, redirect
from .ldapFunctions import LdapCensus
from census.forms import *
from voting.models import Voting
from tablib import Dataset
from .admin import CensusResource
from django.contrib.auth.models import User
from django.db import models
from django.http import HttpResponse
from django.contrib.auth.views import LoginView, LogoutView


class Login(LoginView):
    def get_redirect_url(self):
        return "/census/showAll"

class Logout(LogoutView):

    def get_next_page(self):
        messages.add_message(
                        self.request, messages.SUCCESS, "El usuario ha cerrado sesión correctamente")
        return "/census/showAll"





def register(request):
    if request.method=='POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data['username']
            messages.add_message(
                        request, messages.SUCCESS, "El usuario "+username+" se ha registrado correctamente")
            return redirect('/census/showAll')
    else:
        form = UserRegisterForm()
    context = { 'form':form }
    return render(request, 'register.html', context) 
    
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


def reuseCensus(request, new_voting, old_voting):
    '''
    This function creates new census instances for a new voting, reusing the voters from the census of an already existing voting 
    

    args:

    request:
    new_voting: Identifier of the voting in which we want to reuse the voters
    old_voting: Identifier of the voting from where we want to reuse the voters



    '''

    try:
        voters=Census.objects.filter(voting_id=old_voting).values_list('voter_id', flat=True) 
        votersNoDuplicate = set()
        
        for v in voters:
            votersNoDuplicate.add(v)


        for v in list(votersNoDuplicate): 
            census = Census(voting_id=new_voting, voter_id= v)
            census.save()
    except:
        return HttpResponse('el censo objetivo no está vacio')
  
               

    return HttpResponse('REUTILIZADO CON ÉXITO')

def reuseview(request):
    if request.method == 'POST':
                form = CensusReuseForm(request.POST)
                if form.is_valid():
                    old_voting = form.cleaned_data['oldVoting']
                    new_voting = form.cleaned_data['newVoting']
                    print(old_voting.id,new_voting.id)
                    try:
                        voters=Census.objects.filter(voting_id=old_voting.id).values_list('voter_id', flat=True) 
                        votersNoDuplicate = set()

                        for v in voters:
                            votersNoDuplicate.add(v)


                        for v in list(votersNoDuplicate): 
                            census = Census(voting_id=new_voting.id, voter_id= v)
                            census.save()

                        return HttpResponse('REUTILIZADO CON ÉXITO')


                    except :
                          return HttpResponse('La votación objetivo ya tiene un censo')
    else:
        form = CensusReuseForm()
        context = {
                'form': form
        }
        return render(request, "reuseInterface.html", context)

 








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
        'voting_id': voting_id,
        'format1':"csv",
        'format2':"xls",
        'format3':"json"
    }
    return render(request, "votersInVoting.html", context)


def showVotings(request):
    votings = Voting.objects.all()
    context = {
        'votings': votings,
        'user' : request.user
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

def deleteVoter(request, voting_id, voter_id):
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
    return redirect('/census/showAll')

def importCensusFromLdapVotacion(request):
    """

        This method processes the parameters sent by the form to call the connection method and the import LDAP method
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
                except :
                    messages.add_message(request, messages.ERROR, "Ha ocurrido un error en la conexión con el servido LDAP")            
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
    """
    This method is to import one or multiple census from an .xlsx file. The action needs to be performed by an admin user. 
    
    The method takes the xlsx file and it catches an exception if there is no sent file, then it creates a new
    variable which has the content of the xlsx file. Then it calls the function validate_dataset to make sure there 
    are no mistakes on the file. If there are no mistakes, it saves all the new census, otherwise it will redirect
    to another page with a descriptive message 

    Args:
         request: contains the HTTP data of the form with the .xlsx file
    """
    
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

def validate_dataset(dataset):
    """
    
        This method validate the dataset that enter in the function importar(), we check that the headers and the values
        of the dataset object and are correct to process it. This method returns True if the .xlsx file is correct and 
        False in any other case.

        Args:
            dataset: object with the information of the .xlsx file
            
    """
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
            
def export(request,format):

    """
        This method make a archive contains census datas and you can choose the format of this
    archive with format parameter


    Args:

        request:Request object extends from HttpRequest and this parameter contain metadatos from the request.
        we use to access data.

        format: string reference a type of extension you want to export cesus datas

    """

    census_resource = CensusResource()
    dataset = census_resource.export()
    if format == 'csv':
        response = HttpResponse(dataset.csv, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="census.csv"'
    elif format == 'xls':
        response = HttpResponse(dataset.xls, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename="census.xls"'
    elif format == 'json':
        response = HttpResponse(dataset.json, content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="census.json"'
    else:
        response = HttpResponseBadRequest('Invalid format')
    return response



def exportByVoting(request, format, voting_id):
    """
        This method make a archive contains census datas and you can choose the format of this
    archive with format parameter anf filter from voting_id parameter for export only a specific
    voting


    Args:

        request:Request object extends from HttpRequest and this parameter contain metadatos from the request.
        we use to access data

        format: string reference a type of extension you want to export cesus datas

        voting_id:int reference a ID from voting_id we use this for filter datas for a specific voting.

    """
    census_resourse = CensusResource()
    dataset = census_resourse.export(Census.objects.filter(voting_id=voting_id))
    if format == 'csv':
        response = HttpResponse(dataset.csv, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="census.csv"'
    elif format == 'xls':
        response = HttpResponse(dataset.xls, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename="census.xls"'
    elif format =='json':
        response = HttpResponse(dataset.json, content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="census.json"'
    else:
        response = HttpResponseBadRequest('Invalid format')
    return response

def exportByVoter(request, format, voter_id):
    """
                This method make a archive contains census datas and you can choose the format of this
            archive with format parameter anf filter from voter_id parameter for export
            votings from a specific voter.


            Args:

                request:Request object extends from HttpRequest and this parameter contain metadatos from the request.
                we use to access data

                format: string reference a type of extension you want to export cesus datas

                voter_id:int reference a ID from voter that we use this for filter datas for a specific Voter
    """
    
    census_resourse = CensusResource()
    dataset = census_resourse.export(Census.objects.filter(voter_id=voter_id))
    if format == 'csv':
        response = HttpResponse(dataset.csv, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="census.csv"'
    elif format == 'xls':
        response = HttpResponse(dataset.xls, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename="census.xls"'
    elif format =='json':
        response = HttpResponse(dataset.json, content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="census.json"'
    else:
        response = HttpResponseBadRequest('Invalid format')
    return response

def exportAllCensus(request):
    if request.method == 'POST':
            form = ExportAllCensusForm(request.POST)
            if form.is_valid():
                formato = form.cleaned_data['formato']
                try:
                    census_resource = CensusResource()
                    dataset = census_resource.export()
                    if formato == 'csv':
                        response = HttpResponse(dataset.csv, content_type='text/csv')
                        response['Content-Disposition'] = 'attachment; filename="census.csv"'
                    elif formato == 'xls':
                        response = HttpResponse(dataset.xls, content_type='application/vnd.ms-excel')
                        response['Content-Disposition'] = 'attachment; filename="census.xls"'
                    elif formato == 'json':
                        response = HttpResponse(dataset.json, content_type='application/json')
                        response['Content-Disposition'] = 'attachment; filename="census.json"'
                    else:
                        response = HttpResponseBadRequest('Invalid format')
                    return response
                except :
                     return HttpResponse("Ha ocurrido un error inesperado, sentimos las molestias")
    else:
        form = ExportAllCensusForm()
        context = {
            'form': form
        }
        return render(request, "exportAllCensus.html", context)

def exportCensusByVoter(request):
    if request.method == 'POST':
            form = ExportCensusByVoterForm(request.POST)
            if form.is_valid():
                formato = form.cleaned_data['formato']
                voter = form.cleaned_data['voter']
                try:
                    census_resourse = CensusResource()
                    dataset = census_resourse.export(Census.objects.filter(voter_id=voter.id))
                    if formato == 'csv':
                        response = HttpResponse(dataset.csv, content_type='text/csv')
                        response['Content-Disposition'] = 'attachment; filename="census.csv"'
                    elif formato == 'xls':
                        response = HttpResponse(dataset.xls, content_type='application/vnd.ms-excel')
                        response['Content-Disposition'] = 'attachment; filename="census.xls"'
                    elif formato =='json':
                        response = HttpResponse(dataset.json, content_type='application/json')
                        response['Content-Disposition'] = 'attachment; filename="census.json"'
                    else:
                        response = HttpResponseBadRequest('Invalid format')
                    return response
                except :
                     return HttpResponse("Ha ocurrido un error inesperado, sentimos las molestias")

    else:
        form = ExportCensusByVoterForm()
        context = {
            'form': form
        }
        return render(request, "exportCensusByVoter.html", context)


def exportCensusByVoting(request):
    if request.method == 'POST':
            form = ExportCensusByVotingForm(request.POST)
            if form.is_valid():
                formato = form.cleaned_data['formato']
                voting = form.cleaned_data['voting']
                try:
                    census_resourse = CensusResource()
                    dataset = census_resourse.export(Census.objects.filter(voting_id=voting.id))
                    if formato == 'csv':
                        response = HttpResponse(dataset.csv, content_type='text/csv')
                        response['Content-Disposition'] = 'attachment; filename="census.csv"'
                    elif formato == 'xls':
                        response = HttpResponse(dataset.xls, content_type='application/vnd.ms-excel')
                        response['Content-Disposition'] = 'attachment; filename="census.xls"'
                    elif formato =='json':
                        response = HttpResponse(dataset.json, content_type='application/json')
                        response['Content-Disposition'] = 'attachment; filename="census.json"'
                    else:
                        response = HttpResponseBadRequest('Invalid format')

                    return response
                except :
                     return HttpResponse("Ha ocurrido un error inesperado, sentimos las molestias")

    else:
        form = ExportCensusByVotingForm()
        context = {
            'form': form
        }
        return render(request, "exportCensusByVoting.html", context)
