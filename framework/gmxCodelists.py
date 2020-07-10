import django
import os
import math

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webgis.settings")
django.setup()
from content.models import Country

from xml.etree import ElementTree as ET
from layers.models import ISOcodelist, INSPIREthemes, Layer, Contact
from inspire.models import InpireLayer

import urllib, json

import pandas as pd

def initial_fill_iso_codelist(filename):

    ISOcodelist.objects.all().delete()

    base = os.path.splitext(filename)[0]
    meta_file = base + '.xml'
    if not os.path.exists(meta_file):
        return None

    tree = ET.parse(meta_file)
    root = tree.getroot()


    for codelist in root.findall('{http://www.isotc211.org/2005/gmx}codelistItem'):
        CodeListDictionary = codelist.find('{http://www.isotc211.org/2005/gmx}CodeListDictionary')
        codelist_dict = CodeListDictionary.get('{http://www.opengis.net/gml/3.2}id')

        for code_entry in CodeListDictionary.findall('{http://www.isotc211.org/2005/gmx}codeEntry'):
            code_def = code_entry.find("{http://www.isotc211.org/2005/gmx}CodeDefinition")

            iso_codelist = ISOcodelist(code_list=codelist_dict, identifier=code_def.find("{http://www.opengis.net/gml/3.2}identifier").text, description=code_def.find("{http://www.opengis.net/gml/3.2}description").text)
            iso_codelist.save()

def intitial_fill_inspire_themes():
    both_elements= {}

    path_en = "https://www.eionet.europa.eu/gemet/getTopmostConcepts?thesaurus_uri=http://inspire.ec.europa.eu/theme/&language=en"
    path_de = "https://www.eionet.europa.eu/gemet/getTopmostConcepts?thesaurus_uri=http://inspire.ec.europa.eu/theme/&language=de"

    response_en = urllib.request.urlopen(path_en)
    response_de = urllib.request.urlopen(path_de)

    data_en = json.loads(response_en.read())
    data_de = json.loads(response_de.read())

    # mapping between INSPIRE theme and Topic Category
    data = {}
    data["http://inspire.ec.europa.eu/theme/br"] = "biota"
    data["http://inspire.ec.europa.eu/theme/hb"] = "biota"
    data["http://inspire.ec.europa.eu/theme/sd"] = "biota"
    data["http://inspire.ec.europa.eu/theme/au"] = "boundaries"
    data["http://inspire.ec.europa.eu/theme/su"] = "boundaries"
    data["http://inspire.ec.europa.eu/theme/ac"] = "climatologyMeteorologyAtmosphere"
    data["http://inspire.ec.europa.eu/theme/mf"] = "climatologyMeteorologyAtmosphere"
    data["http://inspire.ec.europa.eu/theme/er"] = "economy"
    data["http://inspire.ec.europa.eu/theme/mr"] = "economy"
    data["http://inspire.ec.europa.eu/theme/el"] = "elevation"
    data["http://inspire.ec.europa.eu/theme/ps"] = "environment"
    data["http://inspire.ec.europa.eu/theme/af"] = "farming"
    data["http://inspire.ec.europa.eu/theme/ge"] = "geoscientificInformation"
    data["http://inspire.ec.europa.eu/theme/nz"] = "geoscientificInformation"
    data["http://inspire.ec.europa.eu/theme/so"] = "geoscientificInformation"
    data["http://inspire.ec.europa.eu/theme/hh"] = "health"
    data["http://inspire.ec.europa.eu/theme/lc"] = "imageryBaseMapsEarthCover"
    data["http://inspire.ec.europa.eu/theme/oi"] = "imageryBaseMapsEarthCover"
    data["http://inspire.ec.europa.eu/theme/hy"] = "inlandWaters"
    data["http://inspire.ec.europa.eu/theme/ad"] = "location"
    data["http://inspire.ec.europa.eu/theme/gn"] = "location"
    data["http://inspire.ec.europa.eu/theme/of"] = "oceans"
    data["http://inspire.ec.europa.eu/theme/sr"] = "oceans"
    data["http://inspire.ec.europa.eu/theme/am"] = "planningCadastre"
    data["http://inspire.ec.europa.eu/theme/cp"] = "planningCadastre"
    data["http://inspire.ec.europa.eu/theme/lu"] = "planningCadastre"
    data["http://inspire.ec.europa.eu/theme/pd"] = "society"
    data["http://inspire.ec.europa.eu/theme/bu"] = "structure"
    data["http://inspire.ec.europa.eu/theme/ef"] = "structure"
    data["http://inspire.ec.europa.eu/theme/pf"] = "structure"
    data["http://inspire.ec.europa.eu/theme/tn"] = "transportation"
    data["http://inspire.ec.europa.eu/theme/us"] = "utilitiesCommunication"

    for element in data_en:
        both_elements[element["uri"]] = {}
        both_elements[element["uri"]]["definition_en"] = element["definition"]["string"]
        both_elements[element["uri"]]["preferredLabel_en"] = element["preferredLabel"]["string"]

    for element in data_de:
        both_elements[element["uri"]]["definition_de"] = element["definition"]["string"]
        both_elements[element["uri"]]["preferredLabel_de"] = element["preferredLabel"]["string"]

    print (both_elements)

    INSPIREthemes.objects.all().delete()
    for value in both_elements:
        print (value)
        print (both_elements[value]["definition_de"])
        if value in data:
            inspire_themes = INSPIREthemes(URI = value, name_en=both_elements[value]['preferredLabel_en'], name_de=both_elements[value]['preferredLabel_de'], definition_de=both_elements[value]['definition_de'], definition_en=both_elements[value]['definition_en'], topicCategory_id=(ISOcodelist.objects.get(identifier=data[value]).id))
        else:
            inspire_themes = INSPIREthemes(URI = value, name_en=both_elements[value]['preferredLabel_en'], name_de=both_elements[value]['preferredLabel_de'], definition_de=both_elements[value]['definition_de'], definition_en=both_elements[value]['definition_en'])

        inspire_themes.save()

def initial_fill_contacts():

   # Contact(city ="Hameln", state = "Germany", organisation="Stadt Hameln - Fachbereich 2: Recht und Sicherheit").save()
   # Contact(city ="Hameln", state = "Germany", organisation="Stadt Hameln - Fachbereich 4: Planen un Bauen").save()
  #  Contact(city ="Hameln", state = "Germany", organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste").save()
    #Contact(city ="Hameln", state = "Germany", organisation="Stadt Hameln - Fachbereich 6: Bildung, Familie und Soziales").save()
    print (Contact.objects.get(organisation="Stadt Hameln - Fachbereich 6: Bildung, Familie und Soziales").id)
    Contact(city ="Hameln", state = "Germany", related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 6: Bildung, Familie und Soziales"), organisation="Stadt Hameln - Fachbereich 6: Bildung, Familie und Soziales / Abteilung 61: Kindertagesbetreuung").save()


def update_topic_cat():
    for item in InpireLayer.objects.all():
        item.topicCategory =  item.inspire_theme.topicCategory
        item.save()

def check_keyword_gemet(keyword = "administration", language = "en"):
    url = "https://www.eionet.europa.eu/gemet/getConceptsMatchingRegexByThesaurus?regex=^" + keyword + "$&thesaurus_uri=http://www.eionet.europa.eu/gemet/concept/&language=" + language
    print (url)
    response = urllib.request.urlopen(url)
    data = json.loads(response.read())
    print (data)
    if len(data) == 0:
        return False
    else:
        return True


def import_excel():
  #  path = "C:\Users\c1zafr\OneDrive\INSPIRE_HM\01_Metadaten\MetadatenerfassungHameln_Abt41.xlsx"
    df = pd.read_excel (r'C:\Users\c1zafr\OneDrive\INSPIRE_HM\01_Metadaten\MetadatenerfassungHameln_Abt41.xlsx', skiprows=6, header=None )
    print (df)
    #df_t = df.transpose()
    #print (df_t)
   # print (df_t["Bearbeiter"])
    print (df.iloc[:,2])
    print(len(df.columns))

    meta = {}

    for i in range(3, len(df.columns)):
        print (df.iloc[:,i])

        meta['title'] = df.iloc[13,i]
        meta['identifier'] = "hameln" + df.iloc[13,i]

        countries = {item.name: item for item in Country.objects.all()}
        meta['country'] = countries["Germany"]

        #meta['meta_date']
        meta['meta_language'] = "en"

        #Metadata Contact
        #shape_data["meta_contact"]

        meta['abstract'] = df.iloc[13,i]

        #shape_data['topic_cat'] use initial from INSPIRE Theme

        #shape_data['keywords'] = [] add read and check keywords from Excel

        # use initial max extent Hameln (needs to be more accurate
        meta['west'] = 9.25
        meta['east'] = 9.46
        meta['south'] = 52.04
        meta['north'] = 52.16

        meta['date_begin'] = df.iloc[13,i]
        meta['date_end'] = df.iloc[13,i]

        #meta['date_publication'] / ....
        meta['meta_lineage'] = df.iloc[13,i]

        meta['resolution_distance'] = df.iloc[13,i]
        #shape_data['resolution_unit'] = "cm"

        #meta['scope']



        # Anwendungseinschränkung

        #meta['ogc_type'] = 'WMTS'

        #shape_data['ogc_attribution'] Stadt Hameln

def import_excel_new():
    #  path = "C:\Users\c1zafr\OneDrive\INSPIRE_HM\01_Metadaten\MetadatenerfassungHameln_Abt41.xlsx"
    df = pd.read_excel (r'C:\Users\c1zafr\OneDrive\INSPIRE_HM\01_Metadaten\Datensätze_GIS_und_INSPIRE.xlsx', skiprows=5, header=None )
    print (df)
    #df_t = df.transpose()
    #print (df_t)
    # print (df_t["Bearbeiter"])
  #  print (df.iloc[:,2])
  #  print(len(df.columns))

    meta = {}
    meta_new = {}
    meta_add = {}

    for i in range(3, len(df)):
        print (df.iloc[i,:])

        # check if inspire relevant and filled
        if (df.iloc[i, 8] == "x" and  len(str(df.iloc[i, 15])) > 4):

            # INSPIRE Theme & topic category
            meta_add["inspire_theme"] = []
            meta_add['topicCategory'] = []

            if (type(df.iloc[i, 9]) is float and not math.isnan(df.iloc[i, 9])):
                themes = df.iloc[i, 9].split(",")

                for theme in themes:
                    item = INSPIREthemes.objects.get(name_de = theme.strip()) #remove tailing & leading whitespaces and search in table
                    print (item)
                    #INSPIRE theme + related topicCategory
                    if (item != None):
                        meta_add["inspire_theme"].append(item.text)
                        meta_add['topicCategory'].append(item.topicCategory.text)
                    else:
                        print ("INSPIRE theme not found. Line:" + str(i) + " " +  item)
            else:
                print ("INSPIRE theme missing" + str(i))

            #Title
            if ((type(df.iloc[i, 16]) is float and not math.isnan(df.iloc[i, 16])) or len(str(df.iloc[i, 16])) > 10):
                meta_new['title'] = df.iloc[i, 16]
                meta_new['identifier'] = "hameln" + df.iloc[i, 16].replace(" ", "_")
            else:
                print ("Title missing or very short. Line:" + str(i) + " " +  str(df.iloc[i, 1]) +" " + str(df.iloc[i, 16]))



            meta_new['title_en'] = df.iloc[i, 17]
            meta_new['alternative_title'] = df.iloc[i, 18]

            countries = {item.name: item for item in Country.objects.all()}
            meta['country'] = countries["Germany"]

            #meta['meta_date']
            meta_new['meta_language'] = "de"

            #Metadata Contact
            #shape_data["meta_contact"]

            meta_new['abstract'] = df.iloc[i, 10]

            if (type(df.iloc[i, 19]) is float and not math.isnan(df.iloc[i, 19])):
                meta_new['abstract_en'] = df.iloc[i, 19]

            if (not math.isnan(df.iloc[i, 20])):
                keywords = df.iloc[i, 20].split(',')
                for keyword in keywords:
                    if check_keyword_gemet(keyword.trim(), "de"):
                        print ("found")
                        #wrtie new keyword
                    else:
                        print ("Keyword not found: Line " + str(i) + " " + keyword )
            else:
                print ("Missing keyword"  + str(i) )

            #shape_data['keywords'] = [] add read and check keywords from Excel

            # use initial max extent Hameln (needs to be more accurate
            meta_new['west'] = 9.25
            meta_new['east'] = 9.46
            meta_new['south'] = 52.04
            meta_new['north'] = 52.16

            meta['date_begin'] = df.iloc[i, 13]
            meta['date_end'] = df.iloc[i, 14]

            #meta['date_publication'] / ....
          #  if (not math.isnan(df.iloc[i,13])):
          #      meta_new['meta_lineage'] = df.iloc[i, 13]
          #  else:
          #      print ("Missing lineage "+ str(i))

            if (not math.isnan(df.iloc[i, 25])):
                meta_new['resolution_distance'] = df.iloc[i, 25]
                meta_new['resolution_unit'] = "cm"
            else:
                print ("Missing resolution "+ str(i))


            #meta['scope']
            meta_new['responsible_city_department_id'] = df.iloc[i, 1]
            print (meta_new)
            layer = InpireLayer(**meta_new)
            layer.save()

            layer.topicCategory.clear()
            if len(meta_add['topicCategory']) > 0:
                for topic_cat in meta_add['topicCategory']:
                    try:
                        layer.topicCategory.add(ISOcodelist.objects.get(identifier=topic_cat).id)
                    except Exception as e:
                        print (str(e))

            layer.inspire_theme.clear()
            for theme in meta_add['topicCategory']:
                try:
                    layer.inspire_theme.add(INSPIREthemes.objects.get(identifier=theme).id)
                except Exception as e:
                    print (str(e))

            break

            # Anwendungseinschränkung

            #meta['ogc_type'] = 'WMTS'

            #shape_data['ogc_attribution'] Stadt Hameln

def initial_fill_country():
    if (Country.objects.filter(name="Germany") != None):
        country = Country(name="Germany", continent="Europe")
        country.save()


def create_seed_data():
    #intitial_fill_inspire_themes()
    #initial_fill_iso_codelist('./gmxCodelists.xml')
    initial_fill_country()

#print (check_keyword_gemet("administration"))
#print (check_keyword_gemet("Verwaltung", "de"))
#import_excel_new()
initial_fill_contacts()

