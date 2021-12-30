import django
from django.db.models import Q
from datetime import datetime
import os
import math
import urllib.parse
import urllib
import json
import pandas as pd
import pandas

from content.models import Country
from layers.models import ISOcodelist, Layer, Contact, KeywordInline, ConstraintConditionsInline
from inspire.models import InspireDataset, InspireTheme, InspireMap, SourceLayer
from map.models import MapGroup, MapLayerInline, MapLayerStyle, KeywordMapInline
from webgis import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webgis.settings")
django.setup()


path_metadata = 'C:/Users/c1zafr/OneDrive/INSPIRE_HM/03_Umsetzung/Zusammenfassung_Metadaten_Dienste.xlsx'
path_metadata_map = r'C:\Users\c1zafr\OneDrive\INSPIRE_HM\01_Metadaten\Datensaetze_GIS_und_INSPIRE_20201110.xlsx'

# def update_topic_cat():
#    for item in InspireLayer.objects.all():
#        item.topicCategory =  item.inspire_theme.topicCategory
#        item.save()

def check_keyword_gemet(keyword="administration", language="en"):
    keyword = urllib.parse.quote(keyword)

    url = "https://www.eionet.europa.eu/gemet/getConceptsMatchingRegexByThesaurus?regex=^" + keyword + "$&thesaurus_uri=http://www.eionet.europa.eu/gemet/concept/&language=" + language
    print(url)

    response = urllib.request.urlopen(url)
    data = json.loads(response.read())
    print(data)
    res = {}
    if len(data) == 0:
        res["found"] = "False"
        return res
    else:
        res["found"] = "True"
        res["URI"] = data[0]['uri']
        return res


def read_keywords(meta_add, keywords, i):
    # Keywords
    if (not type(keywords) is float):
        keywords = keywords.split(',')
        meta_add["keywords"] = []
        meta_add["keywords_not_gemet"] = []
        for keyword in keywords:
            res = check_keyword_gemet(keyword.strip(), "de")
            if res["found"] == "True":
                print("found")
                meta_add["keywords"].append(keyword.strip() + "_" + res["URI"])
                # wrtie new keyword
            else:
                meta_add["keywords_not_gemet"].append(keyword.strip())
                print("Keyword not found: Line " + str(i) + " " + keyword)
    else:
        print("Missing keyword" + str(i))

    return meta_add


def read_theme(meta_add, themes, i):
    # INSPIRE Theme & topic category
    meta_add["inspire_theme"] = []
    meta_add['topicCategory'] = []

    if not type(themes) is float:
        themes_list = themes.split(",")

        for theme in themes_list:
            print(theme.strip())
            item = InspireTheme.objects.get(name_de=theme.strip())  # remove tailing & leading whitespaces and search in table
            print(item)
            # INSPIRE theme + related topicCategory
            if (item != None):
                meta_add["inspire_theme"].append(item)
                meta_add['topicCategory'].append(item.topicCategory)
            else:
                print("INSPIRE theme not found. Line:" + str(i) + " " + item)
    else:
        print("INSPIRE theme missing" + str(i))

    return meta_add


def add_keywords(meta_add, object, type):
    for keyword_uri in meta_add['keywords']:
        print(keyword_uri)
        keyword_uri_arr = keyword_uri.split("_")

        try:
            if type == "layer":
                KeywordInline(keyword=keyword_uri_arr[0], uri=keyword_uri_arr[1], thesaurus_name="http://www.eionet.europa.eu/gemet/concept/",
                              thesaurus_date="2020-02-13", thesaurus_date_type_code_code_value=ISOcodelist.objects.get(identifier="revision"),
                              layer=object).save()
            if type == "map":
                KeywordMapInline(keyword=keyword_uri_arr[0], uri=keyword_uri_arr[1], thesaurus_name="http://www.eionet.europa.eu/gemet/concept/",
                                 thesaurus_date="2020-02-13", thesaurus_date_type_code_code_value=ISOcodelist.objects.get(identifier="revision"),
                                 map=object).save()
        except Exception as e:
            print(str(e))

    for keyword in meta_add["keywords_not_gemet"]:
        print(keyword)
        try:
            if type == "layer":
                KeywordInline(keyword=keyword, layer=object).save()
            if type == "map":
                KeywordMapInline(keyword=keyword, map=object).save()

        except Exception as e:
            print(str(e))


def add_inspire_theme(meta_add, object):
    for theme in meta_add['inspire_theme']:
        print(theme)
    try:
        object.inspire_theme.add(InspireTheme.objects.get(name_en=theme).id)
    except Exception as e:
        print(str(e))


def import_excel_new():
    df = pd.read_excel(path_metadata_map, skiprows=5, header=None)
    print(df)
    # df_t = df.transpose()
    # print (df_t)
    # print (df_t["Bearbeiter"])
    #  print (df.iloc[:,2])
    #  print(len(df.columns))

    SourceLayer.objects.all().delete()

    for i in range(3, len(df)):
        meta = {}
        meta_new = {}
        meta_add = {}

        # check if inspire relevant and filled
        if (df.iloc[i, 8] == "x" and len(str(df.iloc[i, 15])) > 4):
            print(df.iloc[i, :])

            # INSPIRE Theme & topic category
            meta_add = read_theme(meta_add, df.iloc[i, 9], i)

            # Title
            if ((type(df.iloc[i, 15]) is float and not math.isnan(df.iloc[i, 15])) or len(str(df.iloc[i, 15])) > 5):
                meta_new['title'] = df.iloc[i, 15].strip()
                meta_new['identifier'] = df.iloc[i, 32]
            else:
                print("Title missing or very short. Line:" + str(i) + " " + str(df.iloc[i, 1]) + " " + str(df.iloc[i, 15]))

            meta_new['title_en'] = df.iloc[i, 16]

            meta_new['alternative_title'] = df.iloc[i, 17]

            countries = {item.name: item for item in Country.objects.all()}
            meta['country'] = countries["Germany"]

            # meta['meta_date']
            meta_new['meta_language'] = "de"

            # Metadata Contact
            # shape_data["meta_contact"]

            # Abstract
            meta_new['abstract'] = df.iloc[i, 10]
            if type(df.iloc[i, 18]) is float and not math.isnan(df.iloc[i, 18]):
                meta_new['abstract_en'] = df.iloc[i, 18]

            meta_add = read_keywords(meta_add, df.iloc[i, 19], i)

            # shape_data['keywords'] = [] add read and check keywords from Excel

            # use default extent
            meta_new['west'] = settings.DEFAULT_EXTENT_WEST
            meta_new['east'] = settings.DEFAULT_EXTENT_EAST
            meta_new['south'] = settings.DEFAULT_EXTENT_SOUTH
            meta_new['north'] = settings.DEFAULT_EXTENT_NORTH

            # time period
            if check_date(df.iloc[i, 27], i):
                meta_new['date_begin'] = format_date(df.iloc[i, 27])
            if check_date(df.iloc[i, 28], i):
                meta_new['date_end'] = format_date(df.iloc[i, 28])

            if not 'date_begin' in meta_new or not 'date_end' in meta_new:
                print("Missing begin or end date. Line: " + str(i))

            # change dates
            if check_date(df.iloc[i, 21], i):
                meta_new['date_creation'] = format_date(df.iloc[i, 21])
            if check_date(df.iloc[i, 22], i):
                meta_new['date_publication'] = format_date(df.iloc[i, 22])
            if check_date(df.iloc[i, 23], i):
                meta_new['date_revision'] = format_date(df.iloc[i, 23])

            if not 'date_creation' in meta_new and not 'date_publication' not in meta_new and not 'date_revision' in meta_new:
                print("Missing pub, create, revision date!" + str(i))

            # metadata date
            if check_date(df.iloc[i, 23], i):
                meta_new['meta_date'] = format_date(df.iloc[i, 33])

            # progress
            if not type(df.iloc[i, 20]) is float:
                meta_new['progress_id'] = ISOcodelist.objects.get(identifier=get_progressCode(df.iloc[i, 20])).id

            # Demoninator
            if not math.isnan(df.iloc[i, 24]):
                meta_new['denominator'] = df.iloc[i, 24]
            else:
                print("Missing denominator. Line: " + str(i))

            # Resolution
            if not math.isnan(df.iloc[i, 25]):
                meta_new['resolution_distance'] = df.iloc[i, 25]
                meta_new['resolution_unit'] = "cm"
            else:
                print("Missing resolution. Line: " + str(i))

            # EPSG
            if not type(df.iloc[i, 26]) is float:
                if is_integer(df.iloc[i, 26][5:10]):
                    meta_new['dataset_epsg'] = df.iloc[i, 26][5:10]
                else:
                    print("Wrong EPSG format. Line " + str(i) + " " + df.iloc[i, 26][5:10])
            else:
                print("Missing EPSG. Line: " + str(i))

            # Lineage
            if not type(df.iloc[i, 29]) is float:
                meta_new['meta_lineage'] = df.iloc[i, 29]
            else:
                print("Missing lineage. Line: " + str(i))

            # Use limitation
            # ""Es gelten keine Bedingungen" oder "Bedingungen unbekannt" " Nutzungseinschränkungen: Nutzungsbedingungen:
            meta_add['layer_constraints_limit'] = []
            if not type(df.iloc[i, 30]) is float:
                if df.iloc[i, 30] == "keine":
                    meta_add['layer_constraints_limit'].append("Es gelten keine Bedingungen")
                else:
                    meta_add['layer_constraints_limit'].append(df.iloc[i, 30])
            else:
                meta_add['layer_constraints_limit'].append("Bedingungen unbekannt")

            # meta['scope']
            print(df.iloc[i, 1])
            meta_new['internal_responsible_city_department_id'] = Contact.objects.get(
                Q(organisation__contains=str(df.iloc[i, 1]) + ":") & ~Q(organisation__contains=str(df.iloc[i, 1]) + ".")).id
            meta_add['point_of_contacts_id'] = [
                Contact.objects.get(Q(organisation__contains=str(df.iloc[i, 1]) + ":") & ~Q(organisation__contains=str(df.iloc[i, 1]) + ".")).id]
            check_create_new_contact(df.iloc[i, 11], df.iloc[i, 12])
            meta_new['internal_access_constraint'] = df.iloc[i, 13]
            meta_new['internal_legal_basis'] = df.iloc[i, 14]
            print(df.iloc[i, 11])
            meta_new['internal_contact'] = Contact.objects.get(email=df.iloc[i, 12], first_name=df.iloc[i, 11].split(" ")[0])
            meta_new['internal_comment'] = df.iloc[i, 31]
            print(meta_new)
            layer = SourceLayer(**meta_new)
            layer.save()

            layer.topicCategory.clear()
            if len(meta_add['topicCategory']) > 0:
                for topic_cat in meta_add['topicCategory']:
                    try:
                        layer.topicCategory.add(ISOcodelist.objects.get(identifier=topic_cat).id)
                    except Exception as e:
                        print(str(e))

            layer.inspire_theme.clear()
            add_inspire_theme(meta_add, layer)

            # layer.layer_keywords.clear()
            add_keywords(meta_add, layer, "layer")

            ConstraintConditionsInline.objects.filter(layer=layer).delete()
            if meta_add['layer_constraints_limit']:
                for const_cond in meta_add['layer_constraints_limit']:
                    try:
                        ConstraintConditionsInline(constraints_cond=const_cond, layer=layer).save()
                    except Exception as e:
                        print(e)

            layer.point_of_contacts.clear()
            for contact in meta_add['point_of_contacts_id']:
                try:
                    layer.point_of_contacts.add(Contact.objects.get(id=contact).id)
                except Exception as e:
                    print(str(e))
        #  break

        # Anwendungseinschränkung

        # meta['ogc_type'] = 'WMTS'

        # shape_data['ogc_attribution'] Stadt Hameln


def check_create_new_contact(person_name, email):  # first_name last_name
    contacts = {item.first_name + " " + item.last_name: item for item in Contact.objects.all()}

    if person_name not in contacts:
        person = person_name.split(" ")
        contact = Contact(email=email, first_name=person[0], last_name=person[1])
        contact.save()
        contacts[person_name] = contact
        print("New Contact - please edit %s" % ": " + person_name)


def check_date(date, i):
    format = "%d.%m.%Y"
    print (type(date))
    if type(date) is float:  # nan value / empty field
        return False

    if type(date) is pandas._libs.tslibs.timestamps.Timestamp:
        return True

    try:
        datetime.strptime(date, format)
        return True
    except TypeError:
        print("Incorrect date string format. Line: " + str(i) + " " + str(date))
        return False


def is_integer(n):
    try:
        float(n)
    except ValueError:
        return False
    else:
        return float(n).is_integer()


def format_date(date):
    if type(date) is pandas._libs.tslibs.timestamps.Timestamp:
        return date.strftime('%Y-%m-%d')
    else:
        return datetime.strptime(date, "%d.%m.%Y").strftime('%Y-%m-%d')


def get_progressCode(de_progress_identifier):
    progressCode = {}
    progressCode["abgeschlossen"] = "completed"
    progressCode["geplant"] = "planned"
    progressCode["erforderlich"] = "required"
    progressCode["in Erstellung"] = "underDevelopment"
    progressCode["kontinuierliche Aktualisierung"] = "onGoing"
    progressCode["historisches Archiv"] = "historicalArchive"
    progressCode["veraltet"] = "obsolete"

    return progressCode[de_progress_identifier]


def fill_map():
    InspireMap.objects.all().delete()
    MapGroup.objects.all().delete()
    InspireDataset.objects.all().delete()

    xls = pd.ExcelFile(path_metadata)
    new_inspire_ds = pd.read_excel(xls, 'INSPIRE DS', skiprows=1, header=None)  # Dienste_View_Downlod , WMS, WMS Groups
    # print (new_inspire_ds)
    for i in range(0, len(new_inspire_ds)):
        #     print (new_inspire_ds.iloc[i, 1])
        if (new_inspire_ds.iloc[i, 0] == "x"):
            check_create_inspire_layer(new_inspire_ds, i)

    dienste_view_download = pd.read_excel(xls, 'Dienste_View_Download', skiprows=1, header=None)  # Dienste_View_Downlod , WMS, WMS Groups
    # print (dienste_view_downlod)
    for i in range(0, len(dienste_view_download)):
        #     print (dienste_view_downlod.iloc[i, 1])
        if (dienste_view_download.iloc[i, 0] == "x"):
            check_create_dienste_view_download(dienste_view_download, i)

    map_layer = pd.read_excel(xls, 'WMS', skiprows=1, header=None)  # Dienste_View_Downlod , WMS, WMS Groups
    # print (map_layer)
    for i in range(0, len(map_layer)):
        print(map_layer.iloc[i, 1])
        if map_layer.iloc[i, 0] == "x":
            add_map_layer_to_map(map_layer, i)


def check_create_inspire_layer(df, i):
    meta = {}
    meta_new = {}
    meta_add = {}

    # check if inspire relevant and filled
    if df.iloc[i, 0] == "x":
        print(df.iloc[i, :])

        # INSPIRE Theme & topic category
        meta_add = read_theme(meta_add, df.iloc[i, 7], i)

        # Title
        if (type(df.iloc[i, 1]) is float and not math.isnan(df.iloc[i, 1])) or len(str(df.iloc[i, 1])) > 5:
            meta_new['title'] = df.iloc[i, 1].strip()
        else:
            print("Title missing or very short. Line:" + str(i) + " " + str(df.iloc[i, 1]) + " " + str(df.iloc[i, 15]))

        meta_new['identifier'] = df.iloc[i, 15]
        # meta_new['title_en'] = df.iloc[i, 16]

        # meta_new['alternative_title'] = df.iloc[i, 17]

        countries = {item.name: item for item in Country.objects.all()}
        meta['country'] = countries["Germany"]

        # meta['meta_date']
        meta_new['meta_language'] = "de"

        # Metadata Contact
        # shape_data["meta_contact"]

        # Abstract
        meta_new['abstract'] = df.iloc[i, 2]
        # if (type(df.iloc[i, 18]) is float and not math.isnan(df.iloc[i, 18])):
        #     meta_new['abstract_en'] = df.iloc[i, 18]
        print(meta_add)
        # Keywords
        meta_add = read_keywords(meta_add, df.iloc[i, 8], i)

        # use default extent
        meta_new['west'] = settings.DEFAULT_EXTENT_WEST
        meta_new['east'] = settings.DEFAULT_EXTENT_EAST
        meta_new['south'] = settings.DEFAULT_EXTENT_SOUTH
        meta_new['north'] = settings.DEFAULT_EXTENT_NORTH

        # time period #todo
        if check_date(df.iloc[i, 9], i):
            meta_new['date_begin'] = format_date(df.iloc[i, 9])
        if check_date(df.iloc[i, 10], i):
            meta_new['date_end'] = format_date(df.iloc[i, 10])

        # if not 'date_begin' in meta_new or not 'date_end' in meta_new:
        #    print ("Missing begin or end date. Line: " + str(i))

        # change dates
        if check_date(df.iloc[i, 3], i):
            meta_new['date_creation'] = format_date(df.iloc[i, 3])
        #  if check_date(df.iloc[i, 22], i):
        #      meta_new['date_publication'] = format_date(df.iloc[i, 22])
        #  if check_date(df.iloc[i, 23], i):
        #      meta_new['date_revision'] = format_date(df.iloc[i, 23])

        #  if (not 'date_creation' in meta_new and not 'date_publication' not in meta_new and not 'date_revision' in meta_new):
        #      print ("Missing pub, create, revision date!" + str(i))

        # progress #todo
        if not type(df.iloc[i, 11]) is float:
            meta_new['progress_id'] = ISOcodelist.objects.get(identifier=get_progressCode(df.iloc[i, 11])).id

        # Demoninator #todo
        #  if (not math.isnan(df.iloc[i, 24])):
        #      meta_new['denominator'] = df.iloc[i, 24]
        #  else:
        #      print ("Missing denominator. Line: " + str(i))

        # Resolution #todo
        if not math.isnan(df.iloc[i, 12]):
            meta_new['resolution_distance'] = df.iloc[i, 12]
            meta_new['resolution_unit'] = "cm"
        else:
            print("Missing resolution. Line: " + str(i))

        # EPSG
        if not type(df.iloc[i, 6]) is float:
            meta_new['dataset_epsg'] = df.iloc[i, 6]
        else:
            print("Missing EPSG. Line: " + str(i))

        if not type(df.iloc[i, 4]) is float:
            meta_add["data_source"] = {}
            meta_add["data_source"] = df.iloc[i, 4].split(",")
        else:
            print("Missing Source. Line: " + str(i))

        # Lineage
        source_link = ""
        if len(meta_add['data_source']) > 0:
            for data_source in meta_add['data_source']:
                # try:
                print(data_source.strip())
                layer = SourceLayer.objects.get(title__exact=data_source.strip())
                source_link = str(
                    source_link) + " " + layer.title + " (https://geoportal.geodaten.niedersachsen.de/harvest/srv/ger/catalog.search#/metadata/" + str(
                    layer.identifier) + ")"
            # except Exception as e:
            #     print (str(e))

        meta_new[
            'meta_lineage'] = "Der Datensatz setzt sich aus folgenden Quelldaten zusammen: " + source_link + ". Hinweis: Die Quelldaten werden zu unterschiedlichen Zeitpunkten aktualisiert und mit dem jeweiligen Aktualitätsstand in diesem Datensatz abgebildet."

        # Use limitation
        # ""Es gelten keine Bedingungen" oder "Bedingungen unbekannt" " Nutzungseinschränkungen: Nutzungsbedingungen:
        #  meta_add['layer_constraints_limit'] = []
        #  if (not type(df.iloc[i,30]) is float):
        #      if df.iloc[i, 30] == "keine":
        #          meta_add['layer_constraints_limit'].append("Es gelten keine Bedingungen")
        #      else:
        #          meta_add['layer_constraints_limit'].append(df.iloc[i,30])
        #  else:
        #      meta_add['layer_constraints_limit'].append("Bedingungen unbekannt")

        meta_new["meta_file_info"] = df.iloc[i, 14]

        print(meta_add)

        # meta['scope']
        # print(df.iloc[i, 1])
        print(df.iloc[i, 13])

        meta_add['point_of_contacts_id'] = [
            Contact.objects.get(Q(organisation__contains=str(df.iloc[i, 13]) + ":") & ~Q(organisation__contains=str(df.iloc[i, 13]) + ".")).id]
        # except:
        #    print ("Contact not found" + df.iloc[i, 13] + "Line:" + str(i))
        # meta_new['point_of_contacts_id'] = 26
        #   pass
        #  check_create_new_contact(df.iloc[i,11], df.iloc[i,12])
        # meta_new['internal_access_constraint'] = df.iloc[i,13]
        # meta_new['internal_legal_basis'] = df.iloc[i,14]
        # meta_new['internal_contact'] = Contact.objects.get(email=df.iloc[i,12])
        # meta_new['internal_comment'] = df.iloc[i,31]

        #  meta_new[""]
        print(meta_new)
        layer = InspireDataset(**meta_new)
        layer.save()

        # todo
        # meta_new["data_source"] =
        if len(meta_add['data_source']) > 0:
            for data_source in meta_add['data_source']:
                try:
                    layer.data_source.add(SourceLayer.objects.get(title__exact=data_source.strip()).id)
                except Exception as e:
                    print(str(e))

        layer.topicCategory.clear()
        if len(meta_add['topicCategory']) > 0:
            for topic_cat in meta_add['topicCategory']:
                try:
                    layer.topicCategory.add(ISOcodelist.objects.get(identifier=topic_cat).id)
                except Exception as e:
                    print(str(e))

        layer.inspire_theme.clear()
        add_inspire_theme(meta_add, layer)

        # layer.layer_keywords.clear()
        add_keywords(meta_add, layer, "layer")

        layer.point_of_contacts.clear()
        for contact in meta_add['point_of_contacts_id']:
            try:
                layer.point_of_contacts.add(Contact.objects.get(id=contact).id)
            except Exception as e:
                print(str(e))

    #  ConstraintConditionsInline.objects.filter(layer=layer).delete()
    #  if meta_add['layer_constraints_limit']:
    #      for const_cond in meta_add['layer_constraints_limit']:
    #          try:
    #              ConstraintConditionsInline(constraints_cond=const_cond, layer=layer).save()
    #          except Exception as e:
    #              print (e)


def check_create_dienste_view_download(df, i):
    ows_service = {}
    meta_add = {}

    ows_service['ows_contact_id'] = Contact.objects.get(Q(organisation__contains=str(41.3) + ":") & ~Q(organisation__contains=str(41.3) + ".")).id

    ows_service['distributor_contact_id'] = Contact.objects.get(
        Q(organisation__contains=str(df.iloc[i, 4]) + ":") & ~Q(organisation__contains=str(df.iloc[i, 4]) + ".")).id
    ows_service['metadata_contact_id'] = Contact.objects.get(
        Q(organisation__contains=str(df.iloc[i, 5]) + ":") & ~Q(organisation__contains=str(df.iloc[i, 5]) + ".")).id
    ows_service['service_contact_id'] = Contact.objects.get(
        Q(organisation__contains=str(df.iloc[i, 6]) + ":") & ~Q(organisation__contains=str(df.iloc[i, 6]) + ".")).id

    ows_service["service_name"] = df.iloc[i, 1].strip()
    ows_service["service_abstract"] = df.iloc[i, 7].strip()
    ows_service["service_publication_date"] = df.iloc[i, 3]
    ows_service["service_identifier"] = df.iloc[i, 20].strip()
    ows_service["download_name"] = df.iloc[i, 18].strip()
    ows_service["download_abstract"] = df.iloc[i, 7].strip()
    ows_service["download_publication_date"] = df.iloc[i, 3]
    ows_service["download_identifier"] = df.iloc[i, 21].strip()
    ows_service["ows_url_name"] = df.iloc[i, 2].strip()
    ows_service["ows_title_de"] = df.iloc[i, 11].strip()
    ows_service["ows_title_en"] = df.iloc[i, 12].strip()
    ows_service["ows_abstract_de"] = df.iloc[i, 7].strip()
    ows_service["ows_abstract_en"] = df.iloc[i, 8].strip()
    ows_service["ows_style_name"] = df.iloc[i, 17].strip()
    ows_service["ows_rootlayer_title_de"] = df.iloc[i, 13].strip()
    ows_service["ows_rootlayer_title_en"] = df.iloc[i, 14].strip()
    ows_service["ows_rootlayer_abstract_en"] = df.iloc[i, 15].strip()
    ows_service["ows_rootlayer_abstract_de"] = df.iloc[i, 16].strip()

    meta_add = read_keywords(meta_add, df.iloc[i, 10], i)
    meta_add = read_theme(meta_add, df.iloc[i, 9], i)

    print(ows_service)
    inspire_map = InspireMap(**ows_service)
    inspire_map.save()

    # inspire_map.map_keywords.clear()
    add_keywords(meta_add, inspire_map, "map")

    inspire_map.inspire_theme.clear()
    add_inspire_theme(meta_add, inspire_map)

    return inspire_map


def add_map_layer_to_map(df, i):
    # try:
    print(df.iloc[i])
    filter_item = ""
    filter_value = ""
    if (len(str(df.iloc[i, 14])) > 4):
        filter_item = "localId"
        filter_value = '/^' + df.iloc[i, 14] + '*$/'

    MapLayerInline(map=InspireMap.objects.get(service_name=df.iloc[i, 1]), order=df.iloc[i, 4], ows_layer_name=df.iloc[i, 5], ows_layer_title_de=df.iloc[i, 6],
                   ows_layer_title_en=df.iloc[i, 7],
                   ows_layer_abstract_de=df.iloc[i, 8], ows_layer_abstract_en=df.iloc[i, 9], ows_layer_spatial_object_name=df.iloc[i, 10],
                   wms_layer_min_scale=df.iloc[i, 11], wms_layer_max_scale=df.iloc[i, 12], ows_geometry_type=df.iloc[i, 13], ows_filter_item=filter_item,
                   ows_filter_value=filter_value,
                   ows_additional_infos=df.iloc[i, 15],
                   map_layer=InspireDataset.objects.get(title=df.iloc[i, 3])).save()
    # except Exception as e:
    #    print (str(e))


def check_create_wms_group(ows_group_title_de, ows_group_title_en, ows_group_abstract_de, ows_group_abstract_en):
    res = MapGroup.objects.get(ows_group_title_de=ows_group_title_de)
    # create new, if not exists
    if res == None:
        map_group = []

        map_group["ows_group_title_de"] = ows_group_title_de
        map_group["ows_group_title_en"] = ows_group_title_en
        map_group["ows_group_abstract_de"] = ows_group_abstract_de
        map_group["ows_group_abstract_en"] = ows_group_abstract_en
        map_group_obj = SourceLayer(**map_group)
        map_group_obj.save()



# print (check_keyword_gemet("administration"))
# print (check_keyword_gemet("Verwaltung", "de"))

import_excel_new()
fill_map()
