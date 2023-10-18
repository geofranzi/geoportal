import json
import os
import sys
import urllib.parse
from xml.etree import ElementTree as ET

import django


os.chdir("../..")
sys.path.append('')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
sys.path.append('framework')
django.setup()

from climate.models import (CfStandardNames, CoupledModelIntercomparisonProject, GlobalClimateModel,  # noqa: E402
                            Scenario,)
from content.models import Country  # noqa: E402
from inspire.models import InspireTheme  # noqa: E402
from layers.models import (Contact, ISOcodelist, WorkPackage,)  # noqa: E402


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


def initial_fill_country():
    if Country.objects.filter(name="Germany") is not None:
        country = Country(name="Germany", continent="Europe")
        country.save()


def initial_fill_cf_standard_names():
    url = "https://raw.githubusercontent.com/cf-convention/cf-convention.github.io/main/Data/cf-standard-names/current/src/cf-standard-name-table.xml"
    response = urllib.request.urlopen(url)
    # ISOcodelist.objects.all().delete()

    tree = ET.parse(response)
    root = tree.getroot()
    print(tree)
    print(root)
    for entry in root.findall('entry'):
        print(entry.get('id'))
        canonical_units = entry.find('canonical_units')
        grib = entry.find('grib')
        amip = entry.find('amip')
        description = entry.find('description')
        print(grib.text, amip.text, description.text)
        cf_standard = CfStandardNames(entry_id=entry.get("id"), canonical_units=canonical_units.text, grib=grib.text, amip=amip.text,
                                      description=description.text)
        cf_standard.save()


def initial_seed_climate_contacts():
    Contact.objects.all().delete()
    WorkPackage.objects.all().delete()

    WorkPackage(name="WP1", title="Regional projections of future climate change").save()
    WorkPackage(name="WP2", title="Synthesis of comprehensive information on climate change impacts").save()
    WorkPackage(name="WP3", title="Climate Services Gateway through co-production").save()
    WorkPackage(name="WP4", title="Regional Tipping Points and co-development of adaptation options").save()
    WorkPackage(name="WP5", title="Stakeholder engagements (continuous participatory co-production)").save()
    Contact(organisation="Friedrich Schiller University Jena", country="Germany", organisation_short="Uni Jena",
            organisation_ror="https://ror.org/05qpz1x62").save()
    Contact(organisation="Climate Service Center Germany (GERICS), Helmholtz-Zentrum Hereon Hamburg", country="Germany", organisation_short="GERICS",
            website="https://www.climate-service-center.de/", organisation_ror="https://ror.org/022rwzq94").save()
    Contact(organisation="Global Change Institute (GCI) at University of the Witwatersrand (WITS)", country="South Africa", organisation_short="WITS-GCI",
            website="https://www.wits.ac.za/gci/", organisation_ror="https://ror.org/03rp50x72").save()
    Contact(organisation="University of Zambia", country="Zambia", organisation_short="UNZA-IWRMC", website="https://www.unza.zm/",
            organisation_ror="https://ror.org/03gh19d69").save()
    Contact(organisation="University of Botswana", country="Botswana", organisation_short="UB", website="http://www.ub.bw/",
            organisation_ror="https://ror.org/01encsj80").save()
    Contact(organisation="Gobabeb Namib Research Institute", country="Namibia", organisation_short="Gobabeb", website="https://www.gobabeb.org/",
            organisation_ror="https://ror.org/01t6whv16").save()
    Contact(organisation="Namibia University of Science and Technology", country="Namibia", organisation_short="NUST", website="https://www.nust.na/",
            organisation_ror="https://ror.org/03gg1ey66").save()

    team = [
        {
            "title": "Dr.",
            "first_name": "Sophie",
            "last_name": "Biskop",
            "position": "co-project leader & hydrologist",
            "email": "",
            "image": "/biskop.webp",
            "work_packages": ["WP2"],
            "website": "https://www.geographie.uni-jena.de/en/biskop",
            "person_orcid": "",
            "related_org": "Uni Jena"
        },
        {
            "title": "",
            "first_name": "Franziska",
            "last_name": "Zander",
            "position": "research data manager & scientific software developer",
            "email": "",
            "image": "/zander.webp",
            "work_packages": ["WP3"],
            "website": "https://www.geographie.uni-jena.de/en/zander",
            "person_orcid": "0000-0001-6892-7046",
            "related_org": "Uni Jena"
        },
        {
            "title": "Dr.",
            "first_name": "Sven",
            "last_name": "Kralisch",
            "position": "external contractor & scientific software developer",
            "email": "",
            "work_packages": ["WP2", "WP3"],
            "website": "",
            "person_orcid": "0000-0003-2895-540X",
            "related_org": "Uni Jena"
        },
        {
            "title": "Dr.",
            "first_name": "Armelle",
            "last_name": "Remedio",
            "position": "",
            "email": "",
            "work_packages": ["WP1", "WP2"],
            "website": "",
            "person_orcid": "",
            "related_org": "GERICS"
        },
        {
            "title": "Dr.",
            "first_name": "Torsten",
            "last_name": "Weber",
            "position": "Principal Investigator",
            "email": "",
            "work_packages": ["WP1", "WP2"],
            "website": "",
            "person_orcid": "0000-0002-8133-8622",
            "related_org": "GERICS"
        },
        {
            "title": "Dr",
            "first_name": "Bonita",
            "last_name": "De Klerk",
            "position": "",
            "email": "",
            "work_packages": ["WP2"],
            "website": "",
            "person_orcid": "",
            "related_org": "WITS-GCI"
        },
        {
            "title": "Dr.",
            "first_name": "Coleen",
            "last_name": "Vogel",
            "position": "",
            "email": "",
            "work_packages": ["WP5"],
            "website": "",
            "person_orcid": "",
            "related_org": "WITS-GCI"
        },
        {
            "title": "Prof.",
            "first_name": "Francois",
            "last_name": "Engelbrecht",
            "position": "",
            "email": "",
            "work_packages": ["WP1", "WP2", "WP4"],
            "website": "",
            "person_orcid": "0000-0002-9189-6556",
            "related_org": "WITS-GCI"
        },
        {
            "title": "Dr",
            "first_name": "Jessica",
            "last_name": "Steinkopf",
            "position": "",
            "email": "",
            "work_packages": ["WP1", "WP2", "WP4"],
            "website": "https://www.wits.ac.za/gci/staff",
            "person_orcid": "0000-0003-2782-9049",
            "related_org": "WITS-GCI"
        },
        {
            "title": "",
            "first_name": "John",
            "last_name": "McGregor",
            "position": "",
            "email": "",
            "work_packages": ["WP1", "WP2"],
            "website": "",
            "person_orcid": "",
            "related_org": ""
        },
        {
            "title": "",
            "first_name": "Johnathan",
            "last_name": "Padavatan",
            "position": "",
            "email": "",
            "work_packages": ["WP1", "WP2"],
            "website": "https://www.wits.ac.za/gci/staff",
            "person_orcid": "",
            "related_org": "WITS-GCI"
        },
        {
            "title": "Dr",
            "first_name": "Cornelis",
            "last_name": "van der Waal",
            "position": "Postdoc",
            "email": "",
            "work_packages": ["WP4"],
            "website": "",
            "person_orcid": "",
            "related_org": "Gobabeb"
        },
        {
            "title": "",
            "first_name": "Kakunamuua",
            "last_name": "Tjiningire",
            "position": "MSc Student",
            "email": "",
            "work_packages": ["WP4"],
            "website": "",
            "person_orcid": "",
            "related_org": "NUST"
        },
        {
            "title": "Prof",
            "first_name": "Theo",
            "last_name": "Wassenaar",
            "position": "Principal Investigator",
            "email": "",
            "work_packages": ["WP4"],
            "website": "https://www.gobabeb.org/",
            "person_orcid": "",
            "related_org": "NUST"
        },
        {
            "title": "",
            "first_name": "Christina",
            "last_name": "Eins",
            "position": "Postdoc",
            "email": "",
            "work_packages": ["WP4"],
            "website": "",
            "person_orcid": "",
            "related_org": "NUST"
        },
        {
            "title": "",
            "first_name": "Jeremy",
            "last_name": "Perkins",
            "position": "",
            "email": "",
            "work_packages": ["WP4"],
            "website": "",
            "person_orcid": "0000-0002-7396-1430",
            "related_org": "UB"
        },
        {
            "title": "",
            "first_name": "Keabile",
            "last_name": "Tlhalerwa",
            "position": "Researcher",
            "email": "",
            "work_packages": ["WP4"],
            "website": "",
            "person_orcid": "0000-0003-1839-4864",
            "related_org": "UB"
        },
        {
            "title": "",
            "first_name": "Tsaone",
            "last_name": "Goikantswemang",
            "position": "Phd Student",
            "email": "",
            "work_packages": ["WP4"],
            "website": "",
            "person_orcid": "0000-0002-7079-2854",
            "related_org": "UB"
        },
        {
            "title": "",
            "first_name": "Bonang Catherine",
            "last_name": "Mashabana",
            "position": "Phd Student",
            "email": "",
            "work_packages": ["WP4"],
            "website": "",
            "person_orcid": "",
            "related_org": "UB"
        },
        {
            "title": "",
            "first_name": "Koketso",
            "last_name": "Buti",
            "position": "Msc Student",
            "email": "",
            "work_packages": ["WP4"],
            "website": "",
            "person_orcid": "",
            "related_org": "UB"
        },
        {
            "title": "",
            "first_name": "Boago",
            "last_name": "Farinah",
            "position": "Msc Student",
            "email": "",
            "work_packages": ["WP4"],
            "website": "",
            "person_orcid": "",
            "related_org": "UB"
        },
        {
            "title": "",
            "first_name": "Kawawa",
            "last_name": "Banda",
            "position": "",
            "email": "",
            "work_packages": ["WP4"],
            "website": "",
            "person_orcid": "",
            "related_org": "UNZA-IWRMC"
        }
    ]

    for member in team:
        org = Contact.objects.filter(organisation_short=member["related_org"]).first()
        org_id = org.id
        if member["related_org"] == "":
            org_id = None
        print(org_id, member["related_org"])
        contact = Contact(title=member["title"], first_name=member["first_name"], last_name=member["last_name"], position=member["position"],
                          email=member["email"], related_org_id=org_id, website=member["website"], person_orcid=member["person_orcid"])
        contact.save()
        for wp in member["work_packages"]:
            wp_found = WorkPackage.objects.filter(name=wp).first()
            contact.work_packages.add(wp_found.id)

        contact.save()


def initial_seed_climate():
    Scenario(name_short="RCP 2.6", code="rcp26", description="Peak in radiative forcing at ~ 3 W/m2 before 2100 and decline",
             web_url="https://en.wikipedia.org/wiki/RCP_2.6").save()
    Scenario(name_short="RCP 4.5", code="rcp45", description="Stabilization without overshoot pathway to 4.5 W/m2 at stabilization after 2100",
             web_url="https://en.wikipedia.org/wiki/RCP_4.5").save()
    Scenario(name_short="RCP 6.0", code="rcp60", description="Stabilization without overshoot pathway to 6 W/m2 at stabilization after 2100",
             web_url="https://en.wikipedia.org/wiki/RCP_6.0").save()
    Scenario(name_short="RCP 8.5", code="rcp85", description="Rising radiative forcing pathway leading to 8.5 W/m2 in 2100.",
             web_url="https://en.wikipedia.org/wiki/RCP_8.5").save()
    Scenario(name_short="SSP1", name_long="SSP 1: Sustainability - Taking the Green Road", code="ssp1", description="Sustainability - Taking the Green Road",
             web_url="https://en.wikipedia.org/wiki/Shared_Socioeconomic_Pathways").save()
    Scenario(name_short="SSP2", name_long="SSP 2: Middle of the Road", code="ssp2", description="Middle of the Road",
             web_url="https://en.wikipedia.org/wiki/Shared_Socioeconomic_Pathways").save()
    Scenario(name_short="SSP3", name_long="SSP 3: Regional Rivalry - A Rocky Road", code="ssp3", description="Regional Rivalry - A Rocky Road",
             web_url="https://en.wikipedia.org/wiki/Shared_Socioeconomic_Pathways").save()
    Scenario(name_short="SSP4", name_long="SSP 4: Inequality - A Road Divided", code="ssp4", description="Inequality - A Road Divided",
             web_url="https://en.wikipedia.org/wiki/Shared_Socioeconomic_Pathways").save()
    Scenario(name_short="SSP5", name_long="SSP 5: Fossil-fueled Development - Taking the Highway", code="ssp5",
             description="Fossil-fueled Development - Taking the Highway", web_url="https://en.wikipedia.org/wiki/Shared_Socioeconomic_Pathways").save()

    CoupledModelIntercomparisonProject(name_short="CMIP5", code="cmip5", name_long="Coupled Model Intercomparison Project Phase 5",
                                       web_url="https://pcmdi.llnl.gov/mips/cmip5/").save()
    CoupledModelIntercomparisonProject(name_short="CMIP6", code="cmip6", name_long="Coupled Model Intercomparison Project Phase 6",
                                       web_url="https://pcmdi.llnl.gov/CMIP6/").save()

    GlobalClimateModel(name_short="")


def create_seed_data():
    pass
    # initial_fill_iso_codelist('./gmxCodelists.xml')
    # initial_fill_inspire_themes()
    # initial_fill_country()
    # initial_fill_cf_standard_names()
    initial_seed_climate_contacts()


if __name__ == "__main__":
    import django

    django.setup()
    create_seed_data()
