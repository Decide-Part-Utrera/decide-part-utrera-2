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

from base.perms import UserIsStaff
from .models import Census
from tablib import Dataset
from .admin import CensusResource
from django.contrib.auth.models import User
from django.db import models
from django.http import HttpResponse
# from django.Template import Template,Context

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
        voters = Census.objects.filter(voting_id=voting_id).values_list('voter_id', flat=True)
        return Response({'voters': voters})


class CensusDetail(generics.RetrieveDestroyAPIView):

    def destroy(self, request, voting_id, *args, **kwargs):
        voters = request.data.get('voters')
        census = Census.objects.filter(voting_id=voting_id, voter_id__in=voters)
        census.delete()
        return Response('Voters deleted from census', status=ST_204)

    def retrieve(self, request, voting_id, *args, **kwargs):
        voter = request.GET.get('voter_id')
        try:
            Census.objects.get(voting_id=voting_id, voter_id=voter)
        except ObjectDoesNotExist:
            return Response('Invalid voter', status=ST_401)
        return Response('Valid voter')


def fullExport(request,format):
    census_resource = CensusResource()
    dataset = census_resource.export()
    if format == 'csv' or format is None:
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
    census_resourse = CensusResource()
    dataset = census_resourse.export(Census.objects.filter(voting_id=voting_id))
    if format == 'csv' or format is None:
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
    census_resourse = CensusResource()
    dataset = census_resourse.export(Census.objects.filter(voter_id=voter_id))
    if format == 'csv' or format is None:
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



# def import_site(request):
#     doc = open("/home/pablo/decide-part-utrera-2/decide/census/templates/export_prueba.html")
#     plt = Template(doc.read())
#     doc.close()
#     ctx = Context()
#     documento  = plt.render(ctx)

#     return HttpResponse(documento)