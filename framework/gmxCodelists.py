import django
import os

from content.models import Country

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webgis.settings")
django.setup()
from xml.etree import ElementTree as ET
from layers.models import ISOcodelist, INSPIREthemes

import urllib, json

import pandas as pd

def initial_fill_iso_codelist(filename):

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





#print (check_keyword_gemet("administration"))
#print (check_keyword_gemet("Verwaltung", "de"))
#import_excel()
intitial_fill_inspire_themes()
#initial_fill_iso_codelist('./gmxCodelists.xml')

