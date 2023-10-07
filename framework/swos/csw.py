import os.path

from django.contrib.sites.models import Site
from django.template.loader import get_template
from owslib.util import http_post

from layers.models import MetadataSerializer
from swos.models import WetlandLayer
from webgis import settings


#Create insert and delete XML
def create_csw_xml(instance):

    layer = MetadataSerializer(instance)

    tpl = get_template('CSW/full_metadata_insert.xml')

    # Add online resource
    online_resources = []
    ogc_type = instance.ogc_type
    if instance.ogc_type in ['WMS', 'WMTS', 'WFS', 'SOS', 'TMS']:
        ogc_type = 'OGC:%s' % ogc_type
    online_resources.append({'linkage': instance.ogc_link, 'name': instance.ogc_layer, 'protocol': ogc_type })

    # Add download link
    if instance.downloadable == True:
        online_resources.append({'linkage': "http://" + Site.objects.get_current().domain + "/swos/download_as_archive?ids=" + str(instance.id) +"%complete" , 'name': "Download data", 'function': {'identifier': "download"}})

    ctx =({
        'layer': layer.data,
        'keyword_list': ('SWOS', ),
        'parent_identifier': "SWOS",
        'online_resources': online_resources
    })

    md_doc_meta = tpl.render(ctx)
    f = open(settings.MEDIA_ROOT + 'csw/' + str(instance.id) + '_metadata.xml', 'w')
    f.write(md_doc_meta.encode('UTF-8'))

    ctx["csw"] = "1"
    md_doc_csw = tpl.render(ctx)
    f = open(settings.MEDIA_ROOT + 'csw/' + str(instance.id) + '_insert.xml', 'w')
    f.write(md_doc_csw.encode('UTF-8'))


    tpl = get_template('CSW/delete.xml')
    ctx =({
        'identifier': instance.identifier
    })

    md_doc = tpl.render(ctx)
    f = open(settings.MEDIA_ROOT + 'csw/' + str(instance.id) + '_delete.xml', 'w')
    f.write(md_doc.encode('UTF-8'))


def create_record(id):
    response = http_post(settings.CSW_T_PATH, request=open(settings.MEDIA_ROOT + 'csw/' + str(id) + '_insert.xml').read())
    print (response)

def delete_record(id):
    if os.path.isfile(settings.MEDIA_ROOT + 'csw/' + str(id) + '_delete.xml'):
        response = http_post(settings.CSW_T_PATH, request=open(settings.MEDIA_ROOT + 'csw/' + str(id) + '_delete.xml').read())
        print (response)

def create_update_csw(instance, action):
    if action == "update":
        delete_record(instance.id)
    create_csw_xml(instance)
    create_record(instance.id)

def delete_csw(instance):
    delete_record(instance.id)

#Create / update all WetlandLayer CSW records
def create_update_csw_all():
    wetland_layer = WetlandLayer.objects.filter(publishable = True)
    for layer in wetland_layer:
        #print layer.__dict__
        from layers.models import MetadataSerializer
        data = MetadataSerializer(layer).data
        import json
        data_obj = json.loads(json.dumps(data))
        print (data_obj["identifier"] + "%" + data_obj["abstract"]+ "%" + str(data_obj["topicCategory"]) + "%" + str(data_obj["layer_keywords"]) + "%" + str(data_obj["scope"]) + "%" + str(data_obj["layer_conformity"]) + "%" + str(data_obj["layer_constraints_limit"]) + "%" + str(data_obj["layer_constraints_cond"]) + "%" + data_obj["meta_lineage"] + "%" + str(data_obj["point_of_contacts"]))
        create_update_csw(layer, "update")
