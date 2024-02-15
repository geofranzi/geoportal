import glob
import mimetypes
import os
import sys
import requests

from django.http import HttpResponse
from django.http import StreamingHttpResponse
from elasticsearch_dsl import Index
from elasticsearch_dsl.connections import connections 
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ClimateLayer
from .search_es import (ClimateCollectionSearch, ClimateDatasetsCollectionIndex, ClimateDatasetsIndex, ClimateIndicatorIndex, ClimateSearch, ClimateIndicatorSearch)
from .serializer import ClimateLayerSerializer

import xarray as xr
import cf_xarray as cfxr
import tarfile
import pwd
import grp

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
    
    if not request.query_params.get("id"):
        return HttpResponse(status=400, content="ID missing or does not exists")
        
    try:

        climate_layer = ClimateLayer.objects.get(pk=request.query_params.get("id"))
    except ClimateLayer.DoesNotExist:
        climate_layer = None
        return HttpResponse(status=400, content="ID missing or does not exists")
        

    if climate_layer:
        filepath = climate_layer.local_path
        if filepath.endswith(".tar"):
            tar_file_path = filepath
            file = climate_layer.file_name
            extract_to = '/opt/rbis/www/tippecc_data/tmp/'
            file_list = [file]
            
            pattern = "/opt/rbis/www/tippecc_data/**/" + climate_layer.file_name
            for fname in glob.glob(pattern, recursive=True):
                if os.path.isfile(fname):
                    filepath = fname
                    print("File exists: " + filepath)
            
            # if os.path.exists(extract_to + file):
            #     print("File exists: " + file)
            #     pass
            if os.path.exists(filepath) and not filepath.endswith(".tar"):
                print("File exists: " + filepath)
                pass    
            else:
                extract_specific_files(tar_file_path, extract_to, file_list)
                filepath = extract_to + file
        else:
            filepath = filepath + climate_layer.file_name

        print("Text coordinates")
        if  request.query_params.get("latmin") and request.query_params.get("latmax") and request.query_params.get("lonmin") and request.query_params.get("lonmax"):
            print("All true")
            latmin = request.query_params.get("latmin")
            latmax = request.query_params.get("latmax")
            lonmin = request.query_params.get("lonmin")
            lonmax = request.query_params.get("lonmax")
            
            try:
               float(latmin)
               float(latmax)
               float(lonmin)
               float(lonmax) 
            except:
               return HttpResponse(status=400, content="coordinates are not a number")
            
            # Todo: check coordinates within extent
            
            filename, file_extension = os.path.splitext(filepath.split("/")[-1])
            file_out =  extract_to + "/"+ filename + "_tmp_" + str(lonmin) + "%" + str(lonmax) + "%" + str(latmin) + "%" + str(latmax) + file_extension
            print(file_out)
            if os.path.exists(file_out):
                print("File exists: " + file_out)
                pass
            else:
                slice_bbox(filepath, file_out, lonmin, lonmax, latmin, latmax)
            filepath = file_out

        if request.query_params.get("year_start") and request.query_params.get("year_end"):
            begin_year = climate_layer.date_begin.year
            end_year = climate_layer.date_end.year
            
            year_start =  request.query_params.get("year_start")
            year_end = request.query_params.get("year_end")
            
            if not year_start.isdigit() or not year_end.isdigit():
                return HttpResponse(status=400, content="year_start or year_end id not a year")
            
            if int(year_start) <= begin_year or int(year_start) >= end_year or int(year_end) <= begin_year or int(year_end) >= end_year or int(year_end) <  int(year_start):
                return HttpResponse(status=400, content="year_start or year_end outside of possible range")
            

            filename, file_extension = os.path.splitext(filepath.split("/")[-1])
            file_out = extract_to + "/"+ filename + "_" + year_start + "-" + year_end + file_extension
            if os.path.exists(file_out):
                print("File exists: " + file_out)
                pass
            else:
                slice_time(filepath, file_out, year_start, year_end, str(climate_layer.date_begin.year))
            filepath = file_out

        type = mimetypes.guess_type(filepath)[0] or mimetypes.guess_type(filepath)[1]
        # file = open(filepath, "rb")
        # response = HttpResponse(file, content_type=type)
        # response["Content-Disposition"] = "attachment; filename= %s" % os.path.basename(
        #     filepath
        # )
        # return response
        
        url = 'https://leutra.geogr.uni-jena.de/tippecc_data/tmp/' + filepath.split("/")[-1]
        filename = os.path.basename(url)
        r = requests.get(url, stream=True)
        response = StreamingHttpResponse(streaming_content=r)
        response['Content-Disposition'] = "attachement; filename= %s" % os.path.basename(
            filepath
        )
        # return local path instead of URL
        if request.query_params.get("path"):
            if request.query_params.get("path") == "true":
                return HttpResponse(status=200, content=filepath)
                
        return response
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
                hits.append({'score': round(hit.meta.score, 3), 'scenario': hit.scenario, 'gcm': hit.gcm, 'rcm': hit.rcm, 'processing_method': hit.processing_method, 'file_id': hit.file_id})

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

def extract_specific_files(tar_file_path, extract_to, file_list):
    with tarfile.open(tar_file_path, 'r') as tar:
        tar.getmembers()            
        for file_name in file_list:
            for member in tar.getmembers():
                if file_name in str(member):
                    print(member) 
                    try:
                        member.name = os.path.basename(member.name)
                        tar.extract(member, path=extract_to)
                        os.chown(extract_to + file_name, uid, gid)
                    except KeyError:
                        print(f"Warning: File '{file_name}' not found in the tar archive.")


class ElasticsearchIndicators(APIView):
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
        search["year_begin"] = False
        search["year_end"] = False
        search['indicator'] = False
        search['periode'] = False
        search['title'] = False
        search['dataset'] = False

        search["text"] = request.query_params.get("search_text")
        search["variable_abbr"] = request.query_params.get("variable_abbr")
        search['frequency'] = request.query_params.get("frequency")
        search['scenario'] = request.query_params.get("scenario")
        search['gcm'] = request.query_params.get("gcm")
        search['rcm'] = request.query_params.get("rcm")
        search['bias_correction'] = request.query_params.get("bias_correction")
        search['year_begin'] = request.query_params.get("year_begin")
        search['year_end'] = request.query_params.get("year_end")
        search['indicator'] = request.query_params.get("indicator")
        search['periode'] = request.query_params.get("periode")
        search['dataset'] = request.query_params.get("dataset")

        ws = ClimateIndicatorSearch(search)
        count = ws.count()  # Total count of result)
        response = ws[0].execute()  # default size is 10 -> set size to total count

        # print response.__dict__

        finalJSON = {'hits': [], 'facets': []}

        hits = []
        facets = dict()
        list_order = dict()


        for hit in response:
            print(hit.to_dict())

            if hit.meta.index == "climate_indicator_index":
                hits.append({'score': round(hit.meta.score, 3), 'title': hit.rcm})

    
        list_order["indicator"] = 12
        list_order["gcm"] = 13
        list_order["rcm"] = 14
        list_order["variable_name"] = 15
        list_order["periode"] = 16
        list_order["scenario"] = 17
        list_order["indicator"] = 18
        list_order["variable_abbr"] = 21
        list_order["file_id"] = 22
        list_order["year_begin"] = 23
        list_order["year_end"] = 24
        list_order["title"] = 110
        list_order["dataset"] = 110
        
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


def slice_bbox(file, file_out, lonmin, lonmax, latmin, latmax):    
    # cdo=Cdo()
    # cdo.sellonlatbox(lonmin,lonmax,latmin,latmax,input=file,output=file_out,options="-f nc4")
    import subprocess
    path_python = sys.executable
    path_script = os.path.dirname(__file__)
    try:
        subprocess.run([path_python, path_script + '/cdo_calls.py','bbox', file, file_out,lonmin,lonmax,latmin,latmax ], check=True)
    except subprocess.CalledProcessError as e:
        print(f'Command {e.cmd} failed with error {e.returncode}')


def slice_time(file, file_out, year_from, year_to, ref_start):    
    # cdo=Cdo()
    # cdo.seltimestep(1,360, input=file,output=file_out,options="-f nc4")
    import subprocess
    path_python = sys.executable
    path_script = os.path.dirname(__file__)
    try:
        subprocess.run([path_python, path_script + '/cdo_calls.py', 'time', file, file_out, year_from, year_to, ref_start ], check=True)
    except subprocess.CalledProcessError as e:
        print(f'Command {e.cmd} failed with error {e.returncode}')


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
        processing_method = None;
        for file in files:
            variables.append({'variable_abbr': file.variable.variable_abbr,
                              'file_id': file.variable.variable_abbr + "_" + str(climateDatasetCollection.id) + "_" + str(file.id), 'frequency': file.frequency,
                              'start_year': file.date_begin, 'date_begin': file.date_end})
            if file.processing_method:
                processing_method = str(file.processing_method.name)
        obj = ClimateDatasetsCollectionIndex(
            rcm=str(climateDatasetCollection.modellingBase.regional_model),
            gcm=str(climateDatasetCollection.modellingBase.forcing_global_model),
            scenario=str(climateDatasetCollection.scenario),
            processing_method=str(processing_method),
            variables=variables,
        )
        print(obj)
        obj.save()


def read_and_insert_ind_index_data(myPath, dataset_):

    connections.create_connection(hosts='https://leutra.geogr.uni-jena.de:443/es1453d', timeout=20)
    # climate_index = Index('climate_indicator_index')
    # climate_index.delete(ignore=404)
    ClimateIndicatorIndex.init()

    filesList = []

    for path, subdirs, files in os.walk(myPath):
        for name in files:
            filesList.append(os.path.join(path, name))

    theDict = dict()
    for something in filesList:  # Calculate size for all files here.
        theStats = os.stat(something)
        theDict[something] = theStats

    for item in theDict:
        print(item.replace("/opt/rbis/www/", "http://leutra.geogr.uni-jena.de/"), round(theDict[item].st_size / (pow(1024, 2)), 2), "MB")
        if item.endswith("nc"):
            # tar = tarfile.open(item)
            # tar.getmembers()
            # for member in tar.getmembers():
             #    print(member)
                    a = 0
                    title = item.split("/")[-1]
                    if "_rcp" in item:
                        a = 0
                        scenario = title.split("_")[-1].split(".")[0]
                    else:
                        a = 1
                        scenario = ""
               #     path = item
                    

                    print(title)
                    gcm = title.split("_")[(-2 + a)].split(".")[0]
                    
                    print(title.split("_")[-4 + a])
                    if "-" in title.split("_")[-4 + a]:
                        rcm = title.split("_")[-3 + a]
                        start = title.split("_")[(-4 + a)].split("-")[0]
                        end = title.split("_")[(-4 + a)].split("-")[1]
                        
                    else:
                        rcm = ""
                        start = title.split("_")[(-3 + a)].split("-")[0]
                        end = title.split("_")[(-3 + a)].split("-")[1] 
                    indicator = title.split("-")[0].replace("tippecc_", "")[:-5]   
                    
                    
                    
                    obj = ClimateIndicatorIndex(
                      rcm=str(rcm),
                      gcm=str(gcm),
                      scenario=scenario,
                      indicator=indicator,
                      title = title,
                      year_begin = str(start),
                      year_end = str(end),
                      periode = start + "-" + end,
                      dataset = dataset_
                    )
                    print(obj)
                    obj.save()

def read_and_insert_ind_index_slice_data(myPath, dataset_):

    connections.create_connection(hosts='https://leutra.geogr.uni-jena.de:443/es1453d', timeout=20)
    climate_index = Index('climate_indicator_index')
    # climate_index.delete(ignore=404)
    # ClimateIndicatorIndex.init()

    filesList = []

    for path, subdirs, files in os.walk(myPath):
        for name in files:
            filesList.append(os.path.join(path, name))

    theDict = dict()
    for something in filesList:  # Calculate size for all files here.
        theStats = os.stat(something)
        theDict[something] = theStats

    for item in theDict:
        print(item.replace("/opt/rbis/www/", "http://leutra.geogr.uni-jena.de/"), round(theDict[item].st_size / (pow(1024, 2)), 2), "MB")
        if item.endswith("nc"):
            # tar = tarfile.open(item)
            # tar.getmembers()
            # for member in tar.getmembers():
             #    print(member)
                    a = 0
                    title = item.split("/")[-1]
                    if "_rcp" in item:
                        a = 0
                        scenario = title.split("_")[-1].split(".")[0]
                    else:
                        a = 1
                        scenario = ""
               #     path = item
                    

                    print(title)
                    gcm = title.split("_")[(-2 + a)].split(".")[0]
                    
                    print(title.split("_")[-4 + a])
                    if "-" in title.split("_")[-4 + a]:
                        rcm = title.split("_")[-3 + a]
                        # start = title.split("_")[(-4 + a)].split("-")[0]
                        # end = title.split("_")[(-4 + a)].split("-")[1]
                        
                    else:
                        rcm = ""
                        # start = title.split("_")[(-3 + a)].split("-")[0]
                        # end = title.split("_")[(-3 + a)].split("-")[1] 
                    
                    start = title.split("_")[1].split("-")[0]
                    end =title.split("_")[1].split("-")[1]
                    indicator = title.split("-")[1].replace("tippecc_", "")[5:-5]   
                    
                    
                    
                    obj = ClimateIndicatorIndex(
                      rcm=str(rcm),
                      gcm=str(gcm),
                      scenario=scenario,
                      indicator=indicator,
                      title = title,
                      year_begin = str(start),
                      year_end = str(end),
                      periode = start + "-" + end,
                      dataset = dataset_
                    )
                    print(obj)
                    obj.save()


#connections.create_connection(hosts='https://leutra.geogr.uni-jena.de:443/es1453d', timeout=20)
#climate_index = Index('climate_indicator_index')
#climate_index.delete(ignore=404)
#read_and_insert_ind_index_data("/opt/rbis/www/tippecc_data/LANDSURF_indictor/full_period", "monthly")
#read_and_insert_ind_index_slice_data("/opt/rbis/www/tippecc_data/LANDSURF_indictor/slices20", "mean 20 years")
#read_and_insert_ind_index_slice_data("/opt/rbis/www/tippecc_data/LANDSURF_indictor/slices30", "mean 30 years")
# bulk_indexing()