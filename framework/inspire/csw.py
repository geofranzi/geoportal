import os.path

from django.conf import settings
from django.contrib.gis.gdal import DataSource
from django.template.loader import get_template
from owslib.util import http_post

from inspire.models import (InspireMap, InspireMapSerializer, InspireMetadataSerializer, SourceMetadataSerializer,)
from layers.models import MetadataSerializer
from map.models import MapLayerInline


# Create insert and delete XML
def create_csw_xml(instance, type):
    result = {}
    layer = MetadataSerializer(instance)

    keywords_thesaurus = []
    keywords_no_thesaurus = []
    ows_identifier = None

    if type == "inspire":
        tpl = get_template('CSW/INSPIRE_Datensatz.xml')
        layer = InspireMetadataSerializer(instance)
        print(layer.data)

        layer.data["point_of_contacts"][0]["organisation"] = create_org_name_hameln(layer.data["point_of_contacts"][0]["organisation"])

        for keywords in layer.data["layer_keywords"]:
            if keywords["uri"] is not None:
                keywords_thesaurus.append(keywords)
            else:
                keywords_no_thesaurus.append(keywords)

        # search for all maps
        ows_list = MapLayerInline.objects.filter(map_layer_id=instance.id)
        for ows_layer in ows_list:
            map_list = InspireMap.objects.filter(id=ows_layer.map.id)
            for map in map_list:
                # if map.map_keywords ..inspireidentifiziert
                ows_identifier = map.ows_url_name

        if ows_identifier is None:
            result["error"] = True
            result["error_msg"] = "XML not created. Reason: Linked map not found for " + layer.data["title"]
            return result
    if type == "source":
        tpl = get_template('CSW/Source_Datensatz.xml')
        layer = SourceMetadataSerializer(instance)
        print(layer.data)

        layer.data["point_of_contacts"][0]["organisation"] = create_org_name_hameln(layer.data["point_of_contacts"][0]["organisation"])

        for keywords in layer.data["layer_keywords"]:
            if keywords["uri"] is not None:
                keywords_thesaurus.append(keywords)
            else:
                keywords_no_thesaurus.append(keywords)
    print(keywords_no_thesaurus)
    ctx = ({
        'layer': layer.data,
        'keywords_thesaurus': keywords_thesaurus,
        'keywords_no_thesaurus': keywords_no_thesaurus,
        'ows_identifier': ows_identifier
        #  'online_resources': online_resources
    })

    md_doc_meta = tpl.render(ctx)
    f = open(settings.MEDIA_ROOT + '/csw/metadata/' + str(instance.id) + '_' + type + '_metadata.xml', 'wb')
    f.write(md_doc_meta.encode('UTF-8'))

    ctx["csw"] = "1"
    md_doc_csw = tpl.render(ctx)
    f = open(settings.MEDIA_ROOT + '/csw/' + str(instance.id) + '_' + type + '_insert.xml', 'wb')
    f.write(md_doc_csw.encode('UTF-8'))

    print(ows_identifier)

    tpl = get_template('CSW/delete.xml')
    ctx = ({
        'identifier': instance.identifier,
        'ows_identifier': ows_identifier
    })

    md_doc = tpl.render(ctx)
    f = open(settings.MEDIA_ROOT + '/csw/' + str(instance.id) + '_' + type + '_delete.xml', 'wb')
    f.write(md_doc.encode('UTF-8'))

    result["error"] = False
    return result


def create_csw_view_xml(instance, inspire):
    layer = InspireMapSerializer(instance)

    tpl_view = get_template('CSW/INSPIRE_View.xml')
    tpl_download = get_template('CSW/INSPIRE_Download.xml')

    keywords_thesaurus = []
    keywords_no_thesaurus = []
    layer_identifier = []

    if inspire:
        map = InspireMapSerializer(instance)
        # print(map.data)
        ows_srs_list = map.data["ows_srs"].split(",")

        for keywords in map.data["map_keywords"]:
            if keywords["uri"] is not None:
                keywords_thesaurus.append(keywords)
            else:
                keywords_no_thesaurus.append(keywords)

        for layer in map.data["map_layer"]:
            if layer["map_layer"]["identifier"] not in layer_identifier:
                layer_identifier.append(layer["map_layer"]["identifier"])

    # todo layer.inspire_keywords
    # todo inspire themes

    #  print(map.data)
    ctx = ({
        'map': map.data,
        'keywords_thesaurus': keywords_thesaurus,
        'keywords_no_thesaurus': keywords_no_thesaurus,
        'layer_identifier': layer_identifier,
        'ows_srs_list': ows_srs_list
        #  'online_resources': online_resources
    })

    md_doc_meta = tpl_view.render(ctx)
    f = open(settings.MEDIA_ROOT + '/csw/metadata/' + str(instance.id) + '_metadata_service.xml', 'wb')
    f.write(md_doc_meta.encode('UTF-8'))

    md_doc_meta = tpl_download.render(ctx)
    f = open(settings.MEDIA_ROOT + '/csw/metadata/' + str(instance.id) + '_metadata_download.xml', 'wb')
    f.write(md_doc_meta.encode('UTF-8'))

    ctx["csw"] = "1"
    md_doc_csw = tpl_view.render(ctx)
    f = open(settings.MEDIA_ROOT + '/csw/' + str(instance.id) + '_insert_service.xml', 'wb')
    f.write(md_doc_csw.encode('UTF-8'))

    tpl_view = get_template('CSW/delete.xml')
    ctx = ({
        'identifier': instance.service_identifier
    })

    # download

    ctx["csw"] = "1"
    md_doc_csw = tpl_download.render(ctx)
    f = open(settings.MEDIA_ROOT + '/csw/' + str(instance.id) + '_insert_download.xml', 'wb')
    f.write(md_doc_csw.encode('UTF-8'))

    tpl_download = get_template('CSW/delete.xml')
    ctx = ({
        'identifier': instance.download_identifier
    })

    md_doc = tpl_download.render(ctx)
    f = open(settings.MEDIA_ROOT + '/csw/' + str(instance.id) + '_delete_download.xml', 'wb')
    f.write(md_doc.encode('UTF-8'))

    create_map_mapfile(instance, inspire)


def create_map_mapfile(instance, inspire):
    layer = InspireMapSerializer(instance)

    tpl = get_template('CSW/INSPIRE_Map.map')

    keywords_thesaurus = []
    keywords_no_thesaurus = []
    layer_identifier = []
    # layer_source = []
    keywords_arr = []

    if inspire:
        map = InspireMapSerializer(instance)
        map.data["ows_srs_list"] = map.data["ows_srs"].split(",")

        for keywords in map.data["map_keywords"]:
            if keywords["uri"] is not None:
                keywords_thesaurus.append(keywords)
            else:
                keywords_no_thesaurus.append(keywords)
            keywords_arr.append(keywords["keyword"])

        for map_layer in map.data["map_layer"]:
            layer = map_layer["map_layer"]
            layer_identifier.append(layer["identifier"])
            # layer_source.append(layer["source"])
            source = map_layer["layer_gml_name"] = layer["meta_file_info"]
            ds = DataSource(os.path.join(settings.GML_PATH, source + ".gml"))
            print(map_layer)
            layer_gml = ds[0]
            # map_layer["layer_data_name"] = map_layer["ows_layer_name"][3:]

    keyword_list = ','.join(keywords_arr)
    layer_identifier_ids_list = ','.join(layer_identifier)

    print(layer_gml.extent)
    print(layer_gml.extent.tuple)
    print(layer_gml.srs.srid)

    # todo layer.inspire_keywords
    # todo inspire themes

    ctx = ({
        'map': map.data,
        'keywords_thesaurus': keywords_thesaurus,
        'keywords_no_thesaurus': keywords_no_thesaurus,
        'keyword_list': keyword_list,
        'layer_identifier': layer_identifier,
        'layer_identifier_ids_list': layer_identifier_ids_list,
        'extent': str(layer_gml.extent).replace(",", " ").replace("  ", " ").replace("(", "").replace(")", ""),
        'epsg': layer_gml.srs.srid,
        # 'source': source
        #  'online_resources': online_resources
    })

    md_doc_meta = tpl.render(ctx)
    f = open(settings.MEDIA_ROOT + '/map/' + map.data["ows_url_name"] + '.map', 'wb')
    f.write(md_doc_meta.encode('UTF-8'))


def create_record(id):
    response = http_post(settings.CSW_T_PATH, request=open(settings.MEDIA_ROOT + '/csw/' + str(id) + '_insert.xml').read())
    print(response)


def delete_record(id):
    if os.path.isfile(settings.MEDIA_ROOT + 'csw/' + str(id) + '_delete.xml'):
        response = http_post(settings.CSW_T_PATH, request=open(settings.MEDIA_ROOT + '/csw/' + str(id) + '_delete.xml').read())
        print(response)


def create_update_csw(instance, action):
    if action == "update":
        delete_record(instance.id)
    create_csw_xml(instance)
    create_record(instance.id)


def delete_csw(instance):
    delete_record(instance.id)


def create_org_name_hameln(org_name):
    print((org_name))
    org_name_arr = org_name.split("/")
    i = 0
    new_name = "Abteilung "

    for abt in org_name_arr:
        if i == 1:
            new_name += abt.split(":")[1]
        if i > 1:
            new_name += " -" + abt.split(":")[1].strip() + "-"
        i = i + 1
    print((new_name))
    return new_name
