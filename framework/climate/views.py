import mimetypes
import os

from django.http import HttpResponse
from elasticsearch_dsl import Index
from elasticsearch_dsl.connections import connections
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ClimateLayer
from .search_es import (ClimateCollectionSearch, ClimateDatasetsCollectionIndex, ClimateDatasetsIndex, ClimateSearch,)
from .serializer import ClimateLayerSerializer


@api_view(['GET'])
def get_climate_layers(request):
    try:
        climate_layers = ClimateLayer.objects.all()
    except ClimateLayer.DoesNotExist:
        climate_layers = None

    if climate_layers:
        serializer = ClimateLayerSerializer(climate_layers, many=True)
        return Response(serializer.data, status=200)
    else:
        return HttpResponse(status=204)


@api_view(['GET'])
def get_climate_layer(request):
    try:
        climate_layer = ClimateLayer.objects.get(pk=request.query_params.get("id"))
    except ClimateLayer.DoesNotExist:
        climate_layer = None

    if climate_layer:
        serializer = ClimateLayerSerializer(climate_layer)
        return Response(serializer.data, status=200)
    else:
        return HttpResponse(status=204)


@api_view(['GET'])
def download(request):
    try:
        climate_layer = ClimateLayer.objects.get(pk=request.query_params.get("id"))
    except ClimateLayer.DoesNotExist:
        climate_layer = None

    if climate_layer:
        filepath = climate_layer.local_path
        if filepath.endswith(".tar"):
            # unzip the tar file
            pass
        else:
            filepath = filepath + climate_layer.file_name

        type = mimetypes.guess_type(filepath)[0] or mimetypes.guess_type(filepath)[1]
        file = open(filepath, "rb")
        response = response = HttpResponse(file, content_type=type)
        response["Content-Disposition"] = "attachment; filename= %s" % os.path.basename(
            filepath
        )
        return (response, False)
    else:
        return HttpResponse(status=204)


class Elasticsearch(APIView):
    def get(self, request):

        search = dict()
        search["text"] = False
        search["east"] = False
        search["west"] = False
        search["north"] = False
        search["south"] = False
        search["variable_standard_name_cf"] = False
        search["variable_name"] = False
        search["frequency"] = False
        search["scenario"] = False
        search["gcm"] = False
        search["rcm"] = False
        search["bias_correction"] = False
        search["start_year"] = False
        search["end_year"] = False

        search["text"] = request.query_params.get("search_text")
        search['variable_standard_name_cf'] = request.query_params.get("variable_standard_name_cf")
        search['variable_name'] = request.query_params.get("variable_name")
        search['frequency'] = request.query_params.get("frequency")
        search['scenario'] = request.query_params.get("scenario")
        search['gcm'] = request.query_params.get("gcm")
        search['rcm'] = request.query_params.get("rcm")
        search['bias_correction'] = request.query_params.get("bias_correction")
        search['start_year'] = request.query_params.get("start_year")
        search['end_year'] = request.query_params.get("end_year")

        ws = ClimateSearch(search)
        count = ws.count()  # Total count of result)
        response = ws[0:count].execute()  # default size is 10 -> set size to total count

        # print response.__dict__

        finalJSON = {'hits': [], 'facets': []}

        hits = []
        facets = dict()
        list_order = dict()

        # for facet in response.facets:
        #     print facet
        #     for (facet, count, selected) in response.facets[facet]:
        #         print(facet, ' (SELECTED):' if selected else ':', count)

        for hit in response:
            print(hit)
            # topics = []
            # if hasattr(hit, 'topiccat'):
            #     if hit.topiccat:
            #         for topic in hit.topiccat:
            #             topics.append({'val': topic})

            # keywords = []
            # if hasattr(hit, 'keywords'):
            #     print hit.keywords
            #     print hit.meta.id
            #     if hit.keywords:
            #         for keyword in hit.keywords:
            #             keywords.append({'val': keyword})
            if hit.meta.index == "climate_index":
                hits.append({'score': round(hit.meta.score, 3), 'title': hit.title, 'django_id': hit.meta.id, 'description': hit.description, 'path': hit.link,
                             'dataset': hit.dataset})

        list_order["title"] = 11
        list_order["variable_standard_name_cf"] = 12
        list_order["gcm"] = 13
        list_order["rcm"] = 14
        list_order["variable_name"] = 15
        list_order["frequency"] = 16
        list_order["scenario"] = 17
        list_order["bias_correction"] = 18
        list_order["start_year"] = 19
        list_order["end_year"] = 20
        list_order["variable_abbr"] = 21

        facets_ordered = []

        for facet in response.facets:
            for (facet_, count, selected) in response.facets[facet]:
                if len(facet_) > 0:
                    if facet not in facets:
                        facets[facet] = []
                        facets[facet] = [{'name': facet_, 'count': count}]
                        facets_ordered.append({'name': facet, 'order': list_order[facet]})
                    else:
                        facets[facet].append({'name': facet_, 'count': count})

        finalJSON['hits'] = hits
        finalJSON['facets'] = facets
        finalJSON['facets_ordered'] = facets_ordered

        return Response(finalJSON)


class ElasticsearchCollections(APIView):
    def get(self, request):

        search = dict()
        search["text"] = False
        search["east"] = False
        search["west"] = False
        search["north"] = False
        search["south"] = False
        search["variable_abbr"] = False
        search["frequency"] = False
        search["scenario"] = False
        search["gcm"] = False
        search["rcm"] = False
        search["bias_correction"] = False
        search["start_year"] = False
        search["end_year"] = False

        search["text"] = request.query_params.get("search_text")
        search["variable_abbr"] = request.query_params.get("variable_abbr")
        search['frequency'] = request.query_params.get("frequency")
        search['scenario'] = request.query_params.get("scenario")
        search['gcm'] = request.query_params.get("gcm")
        search['rcm'] = request.query_params.get("rcm")
        search['bias_correction'] = request.query_params.get("bias_correction")
        search['start_year'] = request.query_params.get("start_year")
        search['end_year'] = request.query_params.get("end_year")
        search['processing_method'] = request.query_params.get("processing_method")

        ws = ClimateCollectionSearch(search)
        count = ws.count()  # Total count of result)
        response = ws[0:count].execute()  # default size is 10 -> set size to total count

        # print response.__dict__

        finalJSON = {'hits': [], 'facets': []}

        hits = []
        facets = dict()
        list_order = dict()

        # for facet in response.facets:
        #     print facet
        #     for (facet, count, selected) in response.facets[facet]:
        #         print(facet, ' (SELECTED):' if selected else ':', count)

        for hit in response:
            print(hit.to_dict())

            # topics = []
            # if hasattr(hit, 'topiccat'):
            #     if hit.topiccat:
            #         for topic in hit.topiccat:
            #             topics.append({'val': topic})

            # keywords = []
            # if hasattr(hit, 'keywords'):
            #     print hit.keywords
            #     print hit.meta.id
            #     if hit.keywords:
            #         for keyword in hit.keywords:
            #             keywords.append({'val': keyword})
            if hit.meta.index == "climate_collection_index":
                hits.append({'score': round(hit.meta.score, 3), 'title': hit.rcm})

        list_order["title"] = 11
        list_order["variables"] = 12
        list_order["gcm"] = 13
        list_order["rcm"] = 14
        list_order["variable_name"] = 15
        list_order["frequency"] = 16
        list_order["scenario"] = 17
        list_order["processing_method"] = 18
        list_order["start_year"] = 19
        list_order["end_year"] = 20
        list_order["variable_abbr"] = 21
        list_order["file_id"] = 22

        facets_ordered = []

        for facet in response.facets:
            for (facet_, count, selected) in response.facets[facet]:
                if len(facet_) > 0:
                    if facet not in facets:
                        facets[facet] = []
                        facets[facet] = [{'name': facet_, 'count': count}]
                        facets_ordered.append({'name': facet, 'order': list_order[facet]})
                    else:
                        facets[facet].append({'name': facet_, 'count': count})

        finalJSON['hits'] = hits
        finalJSON['facets'] = facets
        finalJSON['facets_ordered'] = facets_ordered

        return Response(finalJSON)


def bulk_indexing():
    from .models import (ClimateLayer, ClimateModelling,)

    # connections.create_connection(hosts='http://localhost:9200', timeout=20)
    connections.create_connection(hosts='https://leutra.geogr.uni-jena.de:443/es1453d', timeout=20)
    climate_index = Index('climate_index')
    climate_index.delete(ignore=404)
    ClimateDatasetsIndex.init()
    [b.indexing() for b in ClimateLayer.objects.all().iterator()]

    climate_collections_index = Index('climate_collection_index')
    climate_collections_index.delete(ignore=404)
    ClimateDatasetsCollectionIndex.init()
    climateDatasetCollections = ClimateModelling.objects.all()
    for climateDatasetCollection in climateDatasetCollections:
        files = ClimateLayer.objects.filter(dataset=climateDatasetCollection.id)
        variables = []
        for file in files:
            variables.append({'variable_abbr': file.variable.variable_abbr,
                              'file_id': file.variable.variable_abbr + "_" + str(climateDatasetCollection.id) + "_" + str(file.id), 'frequency': file.frequency,
                              'start_year': file.date_begin, 'date_begin': file.date_end})

        obj = ClimateDatasetsCollectionIndex(
            rcm=str(climateDatasetCollection.modellingBase.regional_model),
            gcm=str(climateDatasetCollection.modellingBase.forcing_global_model),
            scenario=str(climateDatasetCollection.scenario),

            variables=variables,
        )
        print(obj)
        obj.save()

# bulk_indexing()
