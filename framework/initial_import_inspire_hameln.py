from datetime import datetime

import django
from django.db.models import Q
import os
import math
import urllib.parse

import pandas

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webgis.settings")
django.setup()
from content.models import Country

from xml.etree import ElementTree as ET
from layers.models import ISOcodelist, INSPIREthemes, Layer, Contact, KeywordInline, ConstraintConditionsInline
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
    # to do ---add contact details
    Contact(city ="Hameln", state = "Germany", organisation="Stadt Hameln").save()
    Contact(city ="Hameln", state = "Germany", related_org=Contact.objects.get(organisation="Stadt Hameln"), organisation="Stadt Hameln - Fachbereich 2: Recht und Sicherheit").save()

    Contact(city ="Hameln", state = "Germany", related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 2: Recht und Sicherheit"), organisation="Stadt Hameln - Fachbereich 2: Recht und Sicherheit / Abteilung 22: Ordnung und Straßenverkehr").save()
    Contact(city ="Hameln", state = "Germany", related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 2: Recht und Sicherheit"), organisation="Stadt Hameln - Fachbereich 2: Recht und Sicherheit / Abteilung 27: Feuerwahr").save()

    Contact(city ="Hameln", state = "Germany", related_org=Contact.objects.get(organisation="Stadt Hameln"), organisation="Stadt Hameln - Fachbereich 4: Planen un Bauen").save()

    Contact(city ="Hameln", state = "Germany", related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 4: Planen un Bauen"), organisation="Stadt Hameln - Fachbereich 4: Planen un Bauen / Abteilung 41: Stadtentwicklung und Planung").save()
    Contact(city ="Hameln", state = "Germany", related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 4: Planen un Bauen / Abteilung 41: Stadtentwicklung und Planung"), organisation="Stadt Hameln - Fachbereich 4: Planen un Bauen / Abteilung 41: Stadtentwicklung und Planung / Sachgebiet 41.3: Geoinformation und Vermessung").save()
    Contact(city ="Hameln", state = "Germany", related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 4: Planen un Bauen"), organisation="Stadt Hameln - Fachbereich 4: Planen un Bauen / Abteilung 46: Bauverwaltung und Grundstücksverkehr").save()

    Contact(city ="Hameln", state = "Germany", related_org=Contact.objects.get(organisation="Stadt Hameln"), organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste").save()

    Contact(city ="Hameln", state = "Germany", related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste"), organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste / Abteilung 51: Umwelt").save()
    Contact(city ="Hameln", state = "Germany", related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste / Abteilung 51: Umwelt"), organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste / Abteilung 51: Umwelt / Sachgebiet 51.2: UWB und Immissionsschutz ").save()
    Contact(city ="Hameln", state = "Germany", related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste"), organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste / Abteilung 52: Verkehrsplanung und Sicherheit").save()
    Contact(city ="Hameln", state = "Germany", related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste"), organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste / Abteilung 53: Stadtgrün").save()
    Contact(city ="Hameln", state = "Germany", related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste"), organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste / Abteilung 57: Forstamt").save()

    Contact(city ="Hameln", state = "Germany", related_org=Contact.objects.get(organisation="Stadt Hameln"), organisation="Stadt Hameln - Fachbereich 6: Bildung, Familie und Soziales").save()

    Contact(city ="Hameln", state = "Germany", related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 6: Bildung, Familie und Soziales"), organisation="Stadt Hameln - Fachbereich 6: Bildung, Familie und Soziales / Abteilung 61: Kindertagesbetreuung").save()
    Contact(city ="Hameln", state = "Germany", related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 6: Bildung, Familie und Soziales"), organisation="Stadt Hameln - Fachbereich 6: Bildung, Familie und Soziales / Abteilung 62: Schulen und Sport").save()

def initial_fill_country():
    if (Country.objects.filter(name="Germany") != None):
        country = Country(name="Germany", continent="Europe")
        country.save()

def update_topic_cat():
    for item in InpireLayer.objects.all():
        item.topicCategory =  item.inspire_theme.topicCategory
        item.save()

def check_keyword_gemet(keyword = "administration", language = "en"):
    keyword = urllib.parse.quote(keyword)

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
    #print (df_t["Bearbeiter"])
    print (df.iloc[:,2])
    print(len(df.columns))

def import_excel_new():
    #  path = "C:\Users\c1zafr\OneDrive\INSPIRE_HM\01_Metadaten\MetadatenerfassungHameln_Abt41.xlsx"
    df = pd.read_excel (r'C:\Users\c1zafr\OneDrive\INSPIRE_HM\01_Metadaten\Datensaetze_GIS_und_INSPIRE_20200803_HD_JV.xlsx', skiprows=5, header=None )
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

            if (not type(df.iloc[i, 9]) is float):
                themes = df.iloc[i, 9].split(",")

                for theme in themes:
                    print (theme.strip())
                    item = INSPIREthemes.objects.get(name_de = theme.strip()) #remove tailing & leading whitespaces and search in table
                    print (item)
                    #INSPIRE theme + related topicCategory
                    if (item != None):
                        meta_add["inspire_theme"].append(item)
                        meta_add['topicCategory'].append(item.topicCategory)
                    else:
                        print ("INSPIRE theme not found. Line:" + str(i) + " " +  item)
            else:
                print ("INSPIRE theme missing" + str(i))

            #Title
            if ((type(df.iloc[i, 15]) is float and not math.isnan(df.iloc[i, 15])) or len(str(df.iloc[i, 15])) > 10):
                meta_new['title'] = df.iloc[i, 15]
                meta_new['identifier'] = "hameln" + df.iloc[i, 15].replace(" ", "_")
            else:
                print ("Title missing or very short. Line:" + str(i) + " " +  str(df.iloc[i, 1]) +" " + str(df.iloc[i, 15]))

            meta_new['title_en'] = df.iloc[i, 16]

            meta_new['alternative_title'] = df.iloc[i, 17]

            countries = {item.name: item for item in Country.objects.all()}
            meta['country'] = countries["Germany"]

            #meta['meta_date']
            meta_new['meta_language'] = "de"

            #Metadata Contact
            #shape_data["meta_contact"]

            #Abstract
            meta_new['abstract'] = df.iloc[i, 10]
            if (type(df.iloc[i, 18]) is float and not math.isnan(df.iloc[i, 18])):
                meta_new['abstract_en'] = df.iloc[i, 18]

            #Keywords
            if (not type(df.iloc[i, 19]) is float):
                keywords = df.iloc[i, 19].split(',')
                meta_add["keywords"] = []
                for keyword in keywords:
                    if check_keyword_gemet(keyword.strip(), "de"):
                        print ("found")
                        meta_add["keywords"].append(keyword.strip())
                        #wrtie new keyword
                    else:
                        print ("Keyword not found: Line " + str(i) + " " + keyword )
            else:
                print ("Missing keyword"  + str(i) )

            #shape_data['keywords'] = [] add read and check keywords from Excel

            # use initial max extent Hameln (needs to be more accurate todo)
            meta_new['west'] = 9.25
            meta_new['east'] = 9.46
            meta_new['south'] = 52.04
            meta_new['north'] = 52.16

            # time period
            if check_date(df.iloc[i, 27], i):
                meta_new['date_begin'] = format_date(df.iloc[i, 27])
            if check_date(df.iloc[i, 28], i):
                meta_new['date_end'] = format_date(df.iloc[i, 28])

            if not 'date_begin' in meta_new or not 'date_end' in meta_new:
                print ("Missing begin or end date. Line: " + str(i))

            #change dates
            if check_date(df.iloc[i, 21], i):
                meta_new['date_creation'] = format_date(df.iloc[i, 21])
            if check_date(df.iloc[i, 22], i):
                meta_new['date_publication'] = format_date(df.iloc[i, 22])
            if check_date(df.iloc[i, 23], i):
                meta_new['date_revision'] = format_date(df.iloc[i, 23])

            if (not 'date_creation' in meta_new and not 'date_publication' not in meta_new and not 'date_revision' in meta_new):
                print ("Missing pub, create, revision date!" + str(i))

            #progress
            if (not type(df.iloc[i, 20]) is float):
                meta_new['progress_id'] = ISOcodelist.objects.get(identifier=get_progressCode(df.iloc[i, 20])).id

            # Demoninator
            if (not math.isnan(df.iloc[i, 24])):
                meta_new['denominator'] = df.iloc[i, 24]
            else:
                print ("Missing denominator. Line: " + str(i))

            # Resolution
            if (not math.isnan(df.iloc[i, 25])):
                meta_new['resolution_distance'] = df.iloc[i, 25]
                meta_new['resolution_unit'] = "cm"
            else:
                print ("Missing resolution. Line: "+ str(i))

            # EPSG
            if (not type(df.iloc[i, 26]) is float):
                if (is_integer(df.iloc[i, 26][5:10])):
                    meta_new['dataset_epsg'] = df.iloc[i, 26][5:10]
                else:
                    print ("Wrong EPSG format. Line " + str(i) + " " + df.iloc[i, 26][5:10])
            else:
                print ("Missing EPSG. Line: " + str(i))

            # Lineage
            if (not type(df.iloc[i,29]) is float):
                meta_new['meta_lineage'] = df.iloc[i, 29]
            else:
                 print ("Missing lineage. Line: "+ str(i))

            # Use limitation
            # ""Es gelten keine Bedingungen" oder "Bedingungen unbekannt" " Nutzungseinschränkungen: Nutzungsbedingungen:
            if (not type(df.iloc[i,30]) is float):
                meta_add['layer_constraints_limit'] = []
                if df.iloc[i, 30] == "keine":
                    meta_add['layer_constraints_limit'].append("Es gelten keine Bedingungen")
                else:
                    meta_add['layer_constraints_limit'].append(df.iloc[i,30])
            else:
                meta_add['layer_constraints_limit'].append("Bedingungen unbekannt")


            #meta['scope']
            print(df.iloc[i, 1])
            meta_new['responsible_city_department_id'] = Contact.objects.get(Q(organisation__contains=str(df.iloc[i, 1]) + ":") & ~Q(organisation__contains=str(df.iloc[i, 1]) + ".")).id
            check_create_new_contact(df.iloc[i,11], df.iloc[i,12])
            meta_new['access_constraint'] = df.iloc[i,13]
            meta_new['legal_basis'] = df.iloc[i,14]
            meta_new['internal_contact'] = Contact.objects.get(email=df.iloc[i,12])
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
            for theme in meta_add['inspire_theme']:
                print (theme)
                try:
                    layer.inspire_theme.add(INSPIREthemes.objects.get(name_en=theme).id)
                except Exception as e:
                    print (str(e))

            #layer.layer_keywords.clear()
            for keyword in meta_add['keywords']:
                print (keyword)
                try:
                    KeywordInline(keyword=keyword, thesaurus_name="http://www.eionet.europa.eu/gemet/concept/", thesaurus_date = "2020-02-13", thesaurus_date_type_code_code_value = ISOcodelist.objects.get(identifier="revision"), layer=layer).save()
                except Exception as e:
                    print (str(e))

            ConstraintConditionsInline.objects.filter(layer=layer).delete()
            if meta_add['layer_constraints_limit']:
                for const_cond in meta_add['layer_constraints_limit']:
                    try:
                        ConstraintConditionsInline(constraints_cond=const_cond, layer=layer).save()
                    except Exception as e:
                        print (e)

          #  break

            # Anwendungseinschränkung

            #meta['ogc_type'] = 'WMTS'

            #shape_data['ogc_attribution'] Stadt Hameln

def check_create_new_contact(person_name, email): #first_name last_name
    contacts =   {item.first_name + " " + item.last_name: item for item in Contact.objects.all()}

    if person_name not in contacts:
        person = person_name.split(" ")
        contact = Contact(email=email, first_name=person[0], last_name=person[1])
        contact.save()
        contacts[person_name] = contact
        print ("New Contact - please edit %s" % ": " + person_name)

def check_date(date, i):
    format = "%d.%m.%Y"
    print (type(date))
    if(type(date) is float): # nan value / empty field
        return False

    if(type(date) is pandas._libs.tslibs.timestamps.Timestamp):
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
    if(type(date) is pandas._libs.tslibs.timestamps.Timestamp):
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


def create_seed_data():
    #intitial_fill_inspire_themes()
    #initial_fill_iso_codelist('./gmxCodelists.xml')
    initial_fill_country()
    initial_fill_contacts()

#print (check_keyword_gemet("administration"))
#print (check_keyword_gemet("Verwaltung", "de"))
import_excel_new()



