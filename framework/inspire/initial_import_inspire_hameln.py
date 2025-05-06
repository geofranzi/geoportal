import json
import os
import sys
import urllib.parse
from xml.etree import ElementTree as ET

import django


# os.chdir("..")
sys.path.append("")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
sys.path.append("..")
print(sys.path)
django.setup()

# exclude the following models from the flake8 check
# flake8: noqa
from content.models import Country
from inspire.models import (InspireHDV, InspireTheme,)
from layers.models import (Contact, ISOcodelist,)


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

            iso_codelist = ISOcodelist(code_list=codelist_dict, identifier=code_def.find("{http://www.opengis.net/gml/3.2}identifier").text,
                                       description=code_def.find("{http://www.opengis.net/gml/3.2}description").text)
            iso_codelist.save()


def initial_fill_inspire_themes():
    both_elements = {}

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

    print(both_elements)

    InspireTheme.objects.all().delete()
    for value in both_elements:
        print(value)
        print(both_elements[value]["definition_de"])
        if value in data:
            inspire_themes = InspireTheme(uri=value, name_en=both_elements[value]['preferredLabel_en'], name_de=both_elements[value]['preferredLabel_de'],
                                          definition_de=both_elements[value]['definition_de'], definition_en=both_elements[value]['definition_en'],
                                          topicCategory_id=ISOcodelist.objects.get(identifier=data[value]).id)
        else:
            inspire_themes = InspireTheme(uri=value, name_en=both_elements[value]['preferredLabel_en'], name_de=both_elements[value]['preferredLabel_de'],
                                          definition_de=both_elements[value]['definition_de'], definition_en=both_elements[value]['definition_en'])

        inspire_themes.save()


def initial_inspire_hdv():
    print("initial_inspire_hdv")
    InspireHDV.objects.all().delete()
    InspireHDV(uri="http://data.europa.eu/bna/c_ac64a52d", name_en="Geospatial", name_de="Georaum").save()
    InspireHDV(uri="http://data.europa.eu/bna/c_dd313021", name_en="Earth observation and environment", name_de="Erdbeobachtung und Umwelt").save()
    InspireHDV(uri="http://data.europa.eu/bna/c_164e0bf5", name_en="Meteorological", name_de="Meteorologie").save()
    InspireHDV(uri="http://data.europa.eu/bna/c_e1da4e07", name_en="Statistics", name_de="Statistik").save()
    InspireHDV(uri="http://data.europa.eu/bna/c_a9135398", name_en="Companies and company ownership",
               name_de="Unternehmen und Eigentümerschaft von Unter-nehmen").save()
    InspireHDV(uri="http://data.europa.eu/bna/c_b79e35eb", name_en="Mobility", name_de="Mobilität").save()


def initial_fill_country():
    if Country.objects.filter(name="Germany") is not None:
        country = Country(name="Germany", continent="Europe")
        country.save()


def initial_fill_contacts_hameln():
    # to do ---add contact details
    Contact(city="Hameln", state="Deutschland", address="Rathausplatz 1", postcode="31785", organisation="Stadt Hameln").save()
    Contact(city="Hameln", state="Deutschland", address="Rathausplatz 1", postcode="31785", related_org=Contact.objects.get(organisation="Stadt Hameln"),
            organisation="Stadt Hameln - Fachbereich 2: Recht und Sicherheit").save()

    Contact(city="Hameln", state="Deutschland", address="Rathausplatz 1", postcode="31785",
            related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 2: Recht und Sicherheit"),
            organisation="Stadt Hameln - Fachbereich 2: Recht und Sicherheit / Abteilung 22: Ordnung und Straßenverkehr").save()
    Contact(city="Hameln", state="Deutschland", address="Rathausplatz 1", postcode="31785",
            related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 2: Recht und Sicherheit"),
            organisation="Stadt Hameln - Fachbereich 2: Recht und Sicherheit / Abteilung 27: Feuerwehr").save()

    Contact(city="Hameln", state="Deutschland", address="Rathausplatz 1", postcode="31785", related_org=Contact.objects.get(organisation="Stadt Hameln"),
            organisation="Stadt Hameln - Fachbereich 4: Planen un Bauen").save()

    Contact(city="Hameln", state="Deutschland", address="Rathausplatz 1", postcode="31785", telephone="+49 5151 202-1484", fax="+49 5151 202-1846",
            email="stadtplanung@hameln.de", related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 4: Planen un Bauen"),
            organisation="Stadt Hameln - Fachbereich 4: Planen und Bauen / Abteilung 41: Stadtentwicklung und Planung").save()
    Contact(city="Hameln", state="Deutschland", address="Rathausplatz 1", postcode="31785", telephone="+49 5151 202-3040", fax="+49 5151 202-1266",
            email="gis@hameln.de",
            related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 4: Planen und Bauen / Abteilung 41: Stadtentwicklung und Planung"),
            organisation="Stadt Hameln - Fachbereich 4: Planen und Bauen / Abteilung 41: Stadtentwicklung und Planung / Sachgebiet 41.3: Geoinformation und "
                         "Vermessung").save()
    Contact(city="Hameln", state="Deutschland", address="Rathausplatz 1", postcode="31785",
            related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 4: Planen un Bauen"),
            organisation="Stadt Hameln - Fachbereich 4: Planen und Bauen / Abteilung 46: Bauverwaltung und Grundstücksverkehr").save()

    Contact(city="Hameln", state="Deutschland", address="Rathausplatz 1", postcode="31785", related_org=Contact.objects.get(organisation="Stadt Hameln"),
            organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste").save()

    Contact(city="Hameln", state="Deutschland", address="Rathausplatz 1", postcode="31785", fax="+49 5151 202-1288", email="umwelt@hameln.de",
            related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste"),
            organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste / Abteilung 51: Umwelt und Klimaschutz").save()
    Contact(city="Hameln", state="Deutschland", address="Rathausplatz 1", postcode="31785", telephone="+49 5151 202-1471", fax="+49 5151 202-1288",
            email="umwelt@hameln.de",
            related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste / Abteilung 51: Umwelt und Klimaschutz"),
            organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste / Abteilung 51: Umwelt und Klimaschutz / Sachgebiet 51.1: Untere "
                         "Naturschutzbehörde").save()
    Contact(city="Hameln", state="Deutschland", address="Rathausplatz 1", postcode="31785", telephone="+49 5151 202-1823", fax="+49 5151 202-1288",
            email="umwelt@hameln.de",
            related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste / Abteilung 51: Umwelt und Klimaschutz"),
            organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste / Abteilung 51: Umwelt und Klimaschutz / Sachgebiet 51.2a: Untere "
                         "Wasserbehörde").save()
    Contact(city="Hameln", state="Deutschland", address="Rathausplatz 1", postcode="31785", telephone="+49 5151 202-1959", fax="+49 5151 202-1288",
            email="umwelt@hameln.de",
            related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste / Abteilung 51: Umwelt und Klimaschutz"),
            organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste / Abteilung 51: Umwelt und Klimaschutz / Sachgebiet 51.2b: Untere "
                         "Immissionsschutzbehörde").save()
    Contact(city="Hameln", state="Deutschland", address="Rathausplatz 1", postcode="31785", telephone="+49 5151 202-1574", fax="+49 5151 202-1817",
            email="vermessung@hameln.de", related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste"),
            organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste / Abteilung 52: Verkehrsplanung und Straßenwesen").save()
    Contact(city="Hameln", state="Deutschland", address="Rathausplatz 1", postcode="31785", telephone="", fax="", email="stadtgruen@hameln.de",
            related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste"),
            organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste / Abteilung 53: Stadtgrün").save()
    Contact(city="Hameln", state="Deutschland", address="Rathausplatz 1", postcode="31785", telephone="+49 5151 202-3025", fax=" +49 5151202-3027",
            email="forst@hameln.de", related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste"),
            organisation="Stadt Hameln - Fachbereich 5: Umwelt und technische Dienste / Abteilung 57: Forstamt").save()

    Contact(city="Hameln", state="Deutschland", address="Rathausplatz 1", postcode="31785", telephone="+49 5151 202-3966", email="fachbereich6@hameln.de",
            related_org=Contact.objects.get(organisation="Stadt Hameln"), organisation="Stadt Hameln - Fachbereich 6: Bildung, Familie und Soziales").save()

    Contact(city="Hameln", state="Deutschland", address="Rathausplatz 1", postcode="31785", telephone="+49 5151 202-3229", fax="+49 5151 202-1876",
            email="kindertagesbetreuung@hameln.de", related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 6: Bildung, Familie und Soziales"),
            organisation="Stadt Hameln - Fachbereich 6: Bildung, Familie und Soziales / Abteilung 61: Kindertagesbetreuung").save()
    Contact(city="Hameln", state="Deutschland", address="Rathausplatz 1", postcode="31785", telephone="+49 5151 202-1300", fax="+49 5151 202-1630",
            email="schulenundsport@hameln.de", related_org=Contact.objects.get(organisation="Stadt Hameln - Fachbereich 6: Bildung, Familie und Soziales"),
            organisation="Stadt Hameln - Fachbereich 6: Bildung, Familie und Soziales / Abteilung 62: Schulen und Sport").save()


def create_seed_data():
    # initial_fill_iso_codelist('./gmxCodelists.xml')
    # initial_fill_inspire_themes()
    # initial_fill_country()
    # initial_fill_contacts_hameln()
    print("Creating seed data HDV")
    initial_inspire_hdv()


# create_seed_data()
