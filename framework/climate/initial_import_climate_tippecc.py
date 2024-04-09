import json
import os
import sys
import tarfile
import urllib.parse
import uuid
from xml.etree import ElementTree as ET

import django


os.chdir("../..")
sys.path.append("")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
sys.path.append("framework")
django.setup()

from climate.models import ClimateModelling  # noqa: E402
from climate.models import (CfStandardNames, ClimateChangeScenario, ClimateLayer, ClimateModellingBase,  # noqa
                            ClimatePeriods, ClimateProjections, ClimateVariable, CoupledModelIntercomparisonProject,
                            GlobalClimateModel, ProcessingMethod, RegionalClimateModel,)
from content.models import Country  # noqa: E402
from inspire.models import InspireTheme  # noqa: E402
from layers.models import (Contact, ISOcodelist, WorkPackage,)  # noqa
# noqa: I005, I003


def initial_fill_iso_codelist(filename):
    print(filename)
    filename = "/opt/geoportal_tippecc/geoportal/framework/gmxCodelists.xml"
    ISOcodelist.objects.all().delete()

    base = os.path.splitext(filename)[0]
    print(base)
    meta_file = base + ".xml"
    print(os.path.exists(meta_file))
    if not os.path.exists(meta_file):
        return None

    tree = ET.parse(meta_file)
    root = tree.getroot()

    for codelist in root.findall("{http://www.isotc211.org/2005/gmx}codelistItem"):
        CodeListDictionary = codelist.find(
            "{http://www.isotc211.org/2005/gmx}CodeListDictionary"
        )
        codelist_dict = CodeListDictionary.get("{http://www.opengis.net/gml/3.2}id")

        for code_entry in CodeListDictionary.findall(
            "{http://www.isotc211.org/2005/gmx}codeEntry"
        ):
            code_def = code_entry.find(
                "{http://www.isotc211.org/2005/gmx}CodeDefinition"
            )

            iso_codelist = ISOcodelist(
                code_list=codelist_dict,
                identifier=code_def.find(
                    "{http://www.opengis.net/gml/3.2}identifier"
                ).text,
                description=code_def.find(
                    "{http://www.opengis.net/gml/3.2}description"
                ).text,
            )
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
        both_elements[element["uri"]]["preferredLabel_en"] = element["preferredLabel"][
            "string"
        ]

    for element in data_de:
        both_elements[element["uri"]]["definition_de"] = element["definition"]["string"]
        both_elements[element["uri"]]["preferredLabel_de"] = element["preferredLabel"][
            "string"
        ]

    print(both_elements)

    InspireTheme.objects.all().delete()
    for value in both_elements:
        print(value)
        print(both_elements[value]["definition_de"])
        if value in data:
            inspire_themes = InspireTheme(
                uri=value,
                name_en=both_elements[value]["preferredLabel_en"],
                name_de=both_elements[value]["preferredLabel_de"],
                definition_de=both_elements[value]["definition_de"],
                definition_en=both_elements[value]["definition_en"],
                topicCategory_id=ISOcodelist.objects.get(identifier=data[value]).id,
            )
        else:
            inspire_themes = InspireTheme(
                uri=value,
                name_en=both_elements[value]["preferredLabel_en"],
                name_de=both_elements[value]["preferredLabel_de"],
                definition_de=both_elements[value]["definition_de"],
                definition_en=both_elements[value]["definition_en"],
            )

        inspire_themes.save()


def initial_fill_country():
    if Country.objects.filter(name="Germany") is not None:
        country = Country(name="Germany", continent="Europe")
        country.save()


def initial_fill_cf_standard_names():
    ClimateLayer.objects.all().delete()
    ClimateModelling.objects.all().delete()
    ClimateModellingBase.objects.all().delete()
    ClimateVariable.objects.all().delete()
    ClimateProjections.objects.all().delete()
    ClimatePeriods.objects.all().delete()
    GlobalClimateModel.objects.all().delete()
    RegionalClimateModel.objects.all().delete()
    CoupledModelIntercomparisonProject.objects.all().delete()
    ClimateChangeScenario.objects.all().delete()
    CfStandardNames.objects.all().delete()
    url = "https://raw.githubusercontent.com/cf-convention/cf-convention.github.io/main/Data/cf-standard-names/current/src/cf-standard-name-table.xml"
    response = urllib.request.urlopen(url)
    # ISOcodelist.objects.all().delete()

    tree = ET.parse(response)
    root = tree.getroot()
    print(tree)
    print(root)
    for entry in root.findall("entry"):
        # print(entry.get('id'))
        canonical_units = entry.find("canonical_units")
        grib = entry.find("grib")
        amip = entry.find("amip")
        description = entry.find("description")
        # print(grib.text, amip.text, description.text)
        cf_standard = CfStandardNames(
            entry_id=entry.get("id"),
            canonical_units=canonical_units.text,
            grib=grib.text,
            amip=amip.text,
            description=description.text,
        )
        try:
            cf_standard.save()
        except Exception:
            print(grib.text, amip.text, description.text)
            pass


def initial_seed_climate_contacts():
    Contact.objects.all().delete()
    WorkPackage.objects.all().delete()

    WorkPackage(
        name="WP1", title="Regional projections of future climate change"
    ).save()
    WorkPackage(
        name="WP2",
        title="Synthesis of comprehensive information on climate change impacts",
    ).save()
    WorkPackage(
        name="WP3", title="Climate Services Gateway through co-production"
    ).save()
    WorkPackage(
        name="WP4",
        title="Regional Tipping Points and co-development of adaptation options",
    ).save()
    WorkPackage(
        name="WP5",
        title="Stakeholder engagements (continuous participatory co-production)",
    ).save()
    Contact(
        organisation="Friedrich Schiller University Jena",
        country="Germany",
        organisation_short="Uni Jena",
        organisation_ror="https://ror.org/05qpz1x62",
    ).save()
    Contact(
        organisation="Climate Service Center Germany (GERICS), Helmholtz-Zentrum Hereon Hamburg",
        country="Germany",
        organisation_short="GERICS",
        website="https://www.climate-service-center.de/",
        organisation_ror="https://ror.org/022rwzq94",
    ).save()
    Contact(
        organisation="Global Change Institute (GCI) at University of the Witwatersrand (WITS)",
        country="South Africa",
        organisation_short="WITS-GCI",
        website="https://www.wits.ac.za/gci/",
        organisation_ror="https://ror.org/03rp50x72",
    ).save()
    Contact(
        organisation="University of Zambia",
        country="Zambia",
        organisation_short="UNZA-IWRMC",
        website="https://www.unza.zm/",
        organisation_ror="https://ror.org/03gh19d69",
    ).save()
    Contact(
        organisation="University of Botswana",
        country="Botswana",
        organisation_short="UB",
        website="http://www.ub.bw/",
        organisation_ror="https://ror.org/01encsj80",
    ).save()
    Contact(
        organisation="Gobabeb Namib Research Institute",
        country="Namibia",
        organisation_short="Gobabeb",
        website="https://www.gobabeb.org/",
        organisation_ror="https://ror.org/01t6whv16",
    ).save()
    Contact(
        organisation="Namibia University of Science and Technology",
        country="Namibia",
        organisation_short="NUST",
        website="https://www.nust.na/",
        organisation_ror="https://ror.org/03gg1ey66",
    ).save()

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
            "related_org": "Uni Jena",
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
            "related_org": "Uni Jena",
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
            "related_org": "Uni Jena",
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
            "related_org": "GERICS",
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
            "related_org": "GERICS",
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
            "related_org": "WITS-GCI",
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
            "related_org": "WITS-GCI",
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
            "related_org": "WITS-GCI",
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
            "related_org": "WITS-GCI",
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
            "related_org": "",
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
            "related_org": "WITS-GCI",
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
            "related_org": "Gobabeb",
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
            "related_org": "NUST",
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
            "related_org": "NUST",
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
            "related_org": "NUST",
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
            "related_org": "UB",
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
            "related_org": "UB",
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
            "related_org": "UB",
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
            "related_org": "UB",
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
            "related_org": "UB",
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
            "related_org": "UB",
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
            "related_org": "UNZA-IWRMC",
        },
    ]

    for member in team:
        org = Contact.objects.filter(organisation_short=member["related_org"]).first()
        org_id = org.id
        if member["related_org"] == "":
            org_id = None
        print(org_id, member["related_org"])
        contact = Contact(
            title=member["title"],
            first_name=member["first_name"],
            last_name=member["last_name"],
            position=member["position"],
            email=member["email"],
            related_org_id=org_id,
            website=member["website"],
            person_orcid=member["person_orcid"],
        )
        contact.save()
        for wp in member["work_packages"]:
            wp_found = WorkPackage.objects.filter(name=wp).first()
            contact.work_packages.add(wp_found.id)

        contact.save()


def initial_seed_climate():
    ClimateLayer.objects.all().delete()
    ProcessingMethod.objects.all().delete()
    ClimateModelling.objects.all().delete()
    ClimateModellingBase.objects.all().delete()
    ClimateVariable.objects.all().delete()
    ClimateProjections.objects.all().delete()
    ClimatePeriods.objects.all().delete()
    GlobalClimateModel.objects.all().delete()
    RegionalClimateModel.objects.all().delete()
    CoupledModelIntercomparisonProject.objects.all().delete()
    ClimateChangeScenario.objects.all().delete()
    # return True
    ClimateChangeScenario(
        name_short="RCP2.6",
        name_long="",
        code="rcp26",
        description="Peak in radiative forcing at ~ 3 W/m2 before 2100 and decline",
        web_url="https://en.wikipedia.org/wiki/RCP_2.6",
    ).save()
    ClimateChangeScenario(
        name_short="RCP4.5",
        code="rcp45",
        description="Stabilization without overshoot pathway to 4.5 W/m2 at stabilization after 2100",
        web_url="https://en.wikipedia.org/wiki/RCP_4.5",
    ).save()
    ClimateChangeScenario(
        name_short="RCP6.0",
        code="rcp60",
        description="Stabilization without overshoot pathway to 6 W/m2 at stabilization after 2100",
        web_url="https://en.wikipedia.org/wiki/RCP_6.0",
    ).save()
    ClimateChangeScenario(
        name_short="RCP8.5",
        code="rcp85",
        description="Rising radiative forcing pathway leading to 8.5 W/m2 in 2100.",
        web_url="https://en.wikipedia.org/wiki/RCP_8.5",
    ).save()
    ClimateChangeScenario(
        name_short="SSP1",
        name_long="SSP 1: Sustainability - Taking the Green Road",
        code="ssp1",
        description="Sustainability - Taking the Green Road",
        web_url="https://en.wikipedia.org/wiki/Shared_Socioeconomic_Pathways",
    ).save()
    ClimateChangeScenario(
        name_short="SSP2",
        name_long="SSP 2: Middle of the Road",
        code="ssp2",
        description="Middle of the Road",
        web_url="https://en.wikipedia.org/wiki/Shared_Socioeconomic_Pathways",
    ).save()
    ClimateChangeScenario(
        name_short="SSP3",
        name_long="SSP 3: Regional Rivalry - A Rocky Road",
        code="ssp3",
        description="Regional Rivalry - A Rocky Road",
        web_url="https://en.wikipedia.org/wiki/Shared_Socioeconomic_Pathways",
    ).save()
    ClimateChangeScenario(
        name_short="SSP4",
        name_long="SSP 4: Inequality - A Road Divided",
        code="ssp4",
        description="Inequality - A Road Divided",
        web_url="https://en.wikipedia.org/wiki/Shared_Socioeconomic_Pathways",
    ).save()
    ClimateChangeScenario(
        name_short="SSP5",
        name_long="SSP 5: Fossil-fueled Development - Taking the Highway",
        code="ssp5",
        description="Fossil-fueled Development - Taking the Highway",
        web_url="https://en.wikipedia.org/wiki/Shared_Socioeconomic_Pathways",
    ).save()

    CoupledModelIntercomparisonProject(
        name_short="CMIP5",
        code="cmip5",
        name_long="Coupled Model Intercomparison Project Phase 5",
        web_url="https://pcmdi.llnl.gov/mips/cmip5/",
    ).save()
    CoupledModelIntercomparisonProject(
        name_short="CMIP6",
        code="cmip6",
        name_long="Coupled Model Intercomparison Project Phase 6",
        web_url="https://pcmdi.llnl.gov/CMIP6/",
    ).save()

    GlobalClimateModel(
        name_short="EC-EARTH",
        code="EC-EARTH",
        name_long="European Community Earth System Model",
    ).save()
    GlobalClimateModel(
        name_short="NCC-NorESM1-M",
        code="NCC-NorESM1-M",
        name_long="Norwegian Climate Centre - Norwegian Earth System Model 1 - Medium Resolution",
    ).save()
    GlobalClimateModel(
        name_short="MPI-M-MPI-ESM-LR",
        code="MPI-M-MPI-ESM-LR",
        name_long="Max Planck Institute for Meteorology - Max Planck Institute Earth System Model - Low Resolution",
    ).save()
    GlobalClimateModel(
        name_short="MPI-M-MPI-ESM-MR",
        code="MPI-M-MPI-ESM-MR",
        name_long="Max Planck Institute for Meteorology - Max Planck Institute Earth System Model - Medium Resolution",
    ).save()

    GlobalClimateModel(
        name_short="ECMWF-ERAINT",
        code="ECMWF-ERAINT",
        name_long="European Centre for Medium-Range Weather Forecasts - Interim Reanalysis",
    ).save()
    GlobalClimateModel(
        name_short="MOHC-HadGEM2-ES",
        code="MOHC-HadGEM2-ES",
        name_long="Hadley Centre for Climate Prediction and Research - Met Office Hadley Centre Global  "
        "Environment Model 2 - Earth System",
    ).save()

    RegionalClimateModel(
        name_short="CLMcom-KIT-CCLM5-0-15",
        version="v1",
        code="CLMcom-KIT-CCLM5-0-15",
        name_long="Climate Limited-area Modelling Community - Karlsruhe Institute of Technology  "
        "- Cosmo-Climate Limited-area Modelling 5 - 0.15",
    ).save()
    RegionalClimateModel(
        name_short="GERICS-REMO2015",
        version="v1",
        code="GERICS-REMO2015",
        name_long="German Climate Computing Centre - Regional Model 2015",
    ).save()
    RegionalClimateModel(
        name_short="ICTP-RegCM4-7",
        version="v0",
        code="ICTP-RegCM4-7",
        name_long="International Centre for Theoretical Physics - Regional Climate Model 4 - 7",
    ).save()

    ClimatePeriods(start_date="1981-01-01", end_date="2010-12-31").save()
    ClimatePeriods(start_date="2011-01-01", end_date="2040-12-31").save()
    ClimatePeriods(start_date="2041-01-01", end_date="2070-12-31").save()
    ClimatePeriods(start_date="2071-01-01", end_date="2100-12-31").save()
    ClimatePeriods(start_date="1981-01-01", end_date="2000-12-31").save()
    ClimatePeriods(start_date="2001-01-01", end_date="2020-12-31").save()
    ClimatePeriods(start_date="2021-01-01", end_date="2040-12-31").save()
    ClimatePeriods(start_date="2041-01-01", end_date="2060-12-31").save()
    ClimatePeriods(start_date="2061-01-01", end_date="2080-12-31").save()
    ClimatePeriods(start_date="2081-01-01", end_date="2100-12-31").save()

    climateProjections = ClimateProjections.objects.create(name="30 years")
    climateProjections.ref_period.add(
        ClimatePeriods.objects.filter(
            start_date="1981-01-01", end_date="2010-12-31"
        ).first()
    )
    climateProjections.proj_period.add(
        ClimatePeriods.objects.filter(
            start_date="2011-01-01", end_date="2040-12-31"
        ).first()
    )
    climateProjections.proj_period.add(
        ClimatePeriods.objects.filter(
            start_date="2041-01-01", end_date="2070-12-31"
        ).first()
    )
    climateProjections.proj_period.add(
        ClimatePeriods.objects.filter(
            start_date="2071-01-01", end_date="2100-12-31"
        ).first()
    )
    climateProjections.save()

    climateProjections = ClimateProjections.objects.create(name="20 years")
    climateProjections.ref_period.add(
        ClimatePeriods.objects.filter(
            start_date="1981-01-01", end_date="2000-12-31"
        ).first()
    )
    climateProjections.ref_period.add(
        ClimatePeriods.objects.filter(
            start_date="2001-01-01", end_date="2020-12-31"
        ).first()
    )
    climateProjections.proj_period.add(
        ClimatePeriods.objects.filter(
            start_date="2021-01-01", end_date="2040-12-31"
        ).first()
    )
    climateProjections.proj_period.add(
        ClimatePeriods.objects.filter(
            start_date="2041-01-01", end_date="2060-12-31"
        ).first()
    )
    climateProjections.proj_period.add(
        ClimatePeriods.objects.filter(
            start_date="2061-01-01", end_date="2080-12-31"
        ).first()
    )
    climateProjections.proj_period.add(
        ClimatePeriods.objects.filter(
            start_date="2081-01-01", end_date="2100-12-31"
        ).first()
    )
    climateProjections.save()

    ClimateVariable(
        variable_abbr="tas",
        variable_standard_name_cf=CfStandardNames.objects.filter(
            entry_id="air_temperature"
        ).first(),
        variable_name="Near-Surface Air Temperature",
        variable_cell_methods="time: mean",
        variable_unit="K",
    ).save()
    ClimateVariable(
        variable_abbr="tasmax",
        variable_standard_name_cf=CfStandardNames.objects.filter(
            entry_id="air_temperature"
        ).first(),
        variable_name="Daily Maximum Near-Surface Air Temperature",
        variable_cell_methods="time: maximum within days time: mean over days",
        variable_unit="K",
    ).save()
    ClimateVariable(
        variable_abbr="tasmin",
        variable_standard_name_cf=CfStandardNames.objects.filter(
            entry_id="air_temperature"
        ).first(),
        variable_name="Daily Minimum Near-Surface Air Temperature",
        variable_cell_methods="time: minimum within days time: mean over days",
        variable_unit="K",
    ).save()
    ClimateVariable(
        variable_abbr="pr",
        variable_standard_name_cf=CfStandardNames.objects.filter(
            entry_id="precipitation_flux"
        ).first(),
        variable_name="Precipitation",
        variable_cell_methods="time: mean",
        variable_unit="kg m-2 s-1",
    ).save()
    ClimateVariable(
        variable_abbr="rsds",
        variable_standard_name_cf=CfStandardNames.objects.filter(
            entry_id="surface_downwelling_shortwave_flux_in_air"
        ).first(),
        variable_name="Surface Downwelling Shortwave Radiation",
        variable_cell_methods="time: mean",
        variable_unit="W m-2",
    ).save()
    ClimateVariable(
        variable_abbr="sfcwind",
        variable_standard_name_cf=CfStandardNames.objects.filter(
            entry_id="wind_speed"
        ).first(),
        variable_name="Near-Surface Wind Speed",
        variable_cell_methods="time: mean",
        variable_unit="m s-1",
    ).save()
    ClimateVariable(
        variable_abbr="hurs",
        variable_standard_name_cf=CfStandardNames.objects.filter(
            entry_id="relative_humidity"
        ).first(),
        variable_name="Near-Surface Relative Humidity",
        variable_cell_methods="time: mean",
        variable_unit="%",
    ).save()
    ClimateVariable(
        variable_abbr="prf",
        variable_standard_name_cf=CfStandardNames.objects.filter(
            entry_id="precipitation_flux"
        ).first(),
        variable_name="Precipitation Flux",
        variable_cell_methods="time: mean",
        variable_unit="kg m-2 s-1",
    ).save()

    ClimateModellingBase(
        project=CoupledModelIntercomparisonProject.objects.filter(
            name_short="CMIP5"
        ).first(),
        forcing_global_model=GlobalClimateModel.objects.filter(
            name_short="NCC-NorESM1-M"
        ).first(),
        regional_model=RegionalClimateModel.objects.filter(
            name_short="CLMcom-KIT-CCLM5-0-15"
        ).first(),
        experiment_id="r1i1p1",
    ).save()

    ClimateModelling(
        modellingBase=ClimateModellingBase.objects.last(),
        scenario=ClimateChangeScenario.objects.filter(name_short="RCP8.5").first(),
    ).save()
    ClimateModelling(
        modellingBase=ClimateModellingBase.objects.last(),
        scenario=ClimateChangeScenario.objects.filter(name_short="RCP2.6").first(),
    ).save()

    ClimateModellingBase(
        project=CoupledModelIntercomparisonProject.objects.filter(
            name_short="CMIP5"
        ).first(),
        forcing_global_model=GlobalClimateModel.objects.filter(
            name_short="MOHC-HadGEM2-ES"
        ).first(),
        regional_model=RegionalClimateModel.objects.filter(
            name_short="CLMcom-KIT-CCLM5-0-15"
        ).first(),
        experiment_id="r1i1p1",
    ).save()
    ClimateModelling(
        modellingBase=ClimateModellingBase.objects.last(),
        scenario=ClimateChangeScenario.objects.filter(name_short="RCP8.5").first(),
    ).save()
    ClimateModelling(
        modellingBase=ClimateModellingBase.objects.last(),
        scenario=ClimateChangeScenario.objects.filter(name_short="RCP2.6").first(),
    ).save()

    ClimateModellingBase(
        project=CoupledModelIntercomparisonProject.objects.filter(
            name_short="CMIP5"
        ).first(),
        forcing_global_model=GlobalClimateModel.objects.filter(
            name_short="MPI-M-MPI-ESM-LR"
        ).first(),
        regional_model=RegionalClimateModel.objects.filter(
            name_short="CLMcom-KIT-CCLM5-0-15"
        ).first(),
        experiment_id="r1i1p1",
    ).save()

    ClimateModelling(
        modellingBase=ClimateModellingBase.objects.last(),
        scenario=ClimateChangeScenario.objects.filter(name_short="RCP8.5").first(),
    ).save()
    ClimateModelling(
        modellingBase=ClimateModellingBase.objects.last(),
        scenario=ClimateChangeScenario.objects.filter(name_short="RCP2.6").first(),
    ).save()

    ClimateModellingBase(
        project=CoupledModelIntercomparisonProject.objects.filter(
            name_short="CMIP5"
        ).first(),
        forcing_global_model=GlobalClimateModel.objects.filter(
            name_short="NCC-NorESM1-M"
        ).first(),
        regional_model=RegionalClimateModel.objects.filter(
            name_short="ICTP-RegCM4-7"
        ).first(),
        experiment_id="r1i1p1",
    ).save()

    ClimateModelling(
        modellingBase=ClimateModellingBase.objects.last(),
        scenario=ClimateChangeScenario.objects.filter(name_short="RCP8.5").first(),
    ).save()
    ClimateModelling(
        modellingBase=ClimateModellingBase.objects.last(),
        scenario=ClimateChangeScenario.objects.filter(name_short="RCP2.6").first(),
    ).save()

    ClimateModellingBase(
        project=CoupledModelIntercomparisonProject.objects.filter(
            name_short="CMIP5"
        ).first(),
        forcing_global_model=GlobalClimateModel.objects.filter(
            name_short="MOHC-HadGEM2-ES"
        ).first(),
        regional_model=RegionalClimateModel.objects.filter(
            name_short="ICTP-RegCM4-7"
        ).first(),
        experiment_id="r1i1p1",
    ).save()

    ClimateModelling(
        modellingBase=ClimateModellingBase.objects.last(),
        scenario=ClimateChangeScenario.objects.filter(name_short="RCP8.5").first(),
    ).save()
    ClimateModelling(
        modellingBase=ClimateModellingBase.objects.last(),
        scenario=ClimateChangeScenario.objects.filter(name_short="RCP2.6").first(),
    ).save()

    ClimateModellingBase(
        project=CoupledModelIntercomparisonProject.objects.filter(
            name_short="CMIP5"
        ).first(),
        forcing_global_model=GlobalClimateModel.objects.filter(
            name_short="MPI-M-MPI-ESM-LR"
        ).first(),
        regional_model=RegionalClimateModel.objects.filter(
            name_short="ICTP-RegCM4-7"
        ).first(),
        experiment_id="r1i1p1",
    ).save()

    ClimateModelling(
        modellingBase=ClimateModellingBase.objects.last(),
        scenario=ClimateChangeScenario.objects.filter(name_short="RCP8.5").first(),
    ).save()
    ClimateModelling(
        modellingBase=ClimateModellingBase.objects.last(),
        scenario=ClimateChangeScenario.objects.filter(name_short="RCP2.6").first(),
    ).save()

    ClimateModellingBase(
        project=CoupledModelIntercomparisonProject.objects.filter(
            name_short="CMIP5"
        ).first(),
        forcing_global_model=GlobalClimateModel.objects.filter(
            name_short="NCC-NorESM1-M"
        ).first(),
        regional_model=RegionalClimateModel.objects.filter(
            name_short="GERICS-REMO2015"
        ).first(),
        experiment_id="r1i1p1",
    ).save()

    ClimateModelling(
        modellingBase=ClimateModellingBase.objects.last(),
        scenario=ClimateChangeScenario.objects.filter(name_short="RCP8.5").first(),
    ).save()
    ClimateModelling(
        modellingBase=ClimateModellingBase.objects.last(),
        scenario=ClimateChangeScenario.objects.filter(name_short="RCP2.6").first(),
    ).save()

    ClimateModellingBase(
        project=CoupledModelIntercomparisonProject.objects.filter(
            name_short="CMIP5"
        ).first(),
        forcing_global_model=GlobalClimateModel.objects.filter(
            name_short="MOHC-HadGEM2-ES"
        ).first(),
        regional_model=RegionalClimateModel.objects.filter(
            name_short="GERICS-REMO2015"
        ).first(),
        experiment_id="r1i1p1",
    ).save()

    ClimateModelling(
        modellingBase=ClimateModellingBase.objects.last(),
        scenario=ClimateChangeScenario.objects.filter(name_short="RCP8.5").first(),
    ).save()
    ClimateModelling(
        modellingBase=ClimateModellingBase.objects.last(),
        scenario=ClimateChangeScenario.objects.filter(name_short="RCP2.6").first(),
    ).save()

    ClimateModellingBase(
        project=CoupledModelIntercomparisonProject.objects.filter(
            name_short="CMIP5"
        ).first(),
        forcing_global_model=GlobalClimateModel.objects.filter(
            name_short="MPI-M-MPI-ESM-LR"
        ).first(),
        regional_model=RegionalClimateModel.objects.filter(
            name_short="GERICS-REMO2015"
        ).first(),
        experiment_id="r1i1p1",
    ).save()

    ClimateModelling(
        modellingBase=ClimateModellingBase.objects.last(),
        scenario=ClimateChangeScenario.objects.filter(name_short="RCP8.5").first(),
    ).save()
    ClimateModelling(
        modellingBase=ClimateModellingBase.objects.last(),
        scenario=ClimateChangeScenario.objects.filter(name_short="RCP2.6").first(),
    ).save()

    ClimateModellingBase(
        project=CoupledModelIntercomparisonProject.objects.filter(
            name_short="CMIP5"
        ).first(),
        forcing_global_model=GlobalClimateModel.objects.filter(
            name_short="MPI-M-MPI-ESM-MR"
        ).first(),
        regional_model=RegionalClimateModel.objects.filter(
            name_short="ICTP-RegCM4-7"
        ).first(),
        experiment_id="r1i1p1",
    ).save()

    ClimateModelling(
        modellingBase=ClimateModellingBase.objects.last(),
        scenario=ClimateChangeScenario.objects.filter(name_short="RCP8.5").first(),
    ).save()
    ClimateModelling(
        modellingBase=ClimateModellingBase.objects.last(),
        scenario=ClimateChangeScenario.objects.filter(name_short="RCP2.6").first(),
    ).save()

    ProcessingMethod(name="Bias corrected").save()


def read_and_insert_data(myPath, processing):

    filesList = []

    for path, subdirs, files in os.walk(myPath):
        for name in files:
            filesList.append(os.path.join(path, name))

    theDict = dict()
    for something in filesList:  # Calculate size for all files here.
        theStats = os.stat(something)
        theDict[something] = theStats

    for item in theDict:
        print(
            item.replace("/opt/rbis/www/", "http://leutra.geogr.uni-jena.de/"),
            round(theDict[item].st_size / (pow(1024, 2)), 2),
            "MB",
        )
        if item.endswith("tar"):
            tar = tarfile.open(item)
            tar.getmembers()
            for member in tar.getmembers():
                print(member)
                if member.name.endswith(".nc"):
                    path = item
                    title = member.name.split("/")[-1]
                    variable = title.split("_")[4]
                    gcm = title.split("_")[3]
                    rcm = title.split("_")[1]
                    start = title.split("_")[7]
                    end = title.split("_")[8].split(".")[0]
                    if not ClimateLayer.objects.filter(title=title).first():
                        insert_climate_data(
                            path,
                            title,
                            variable,
                            gcm,
                            rcm,
                            member.size,
                            processing,
                            start,
                            end,
                        )
        if item.endswith(".nc"):
            path = item
            title = item.split("/")[-1]
            variable = title.split("_")[4]
            gcm = title.split("_")[3]
            rcm = title.split("_")[1]
            start = title.split("_")[7]
            end = title.split("_")[8].split(".")[0]
            insert_climate_data(path, title, variable, gcm, rcm, theDict[item].st_size, processing, start, end)
    # add info for unpacked files


def test_instet_climate_data():
    path = "/opt/rbis/www/TIPPECC_CLMcom-KIT-CCLM5-0-15_v1_NCC-NorESM1-M_pr_Afr_day_1950_2100.nc"
    # TIPPECC_CLMcom-KIT-CCLM5-0-15_v1_NCC-NorESM1-M_tas_Afr_day_1950_2100.nc"
    title = path.split("/")[-1]
    variable = title.split("_")[4]
    gcm = title.split("_")[3]
    rcm = title.split("_")[1]
    insert_climate_data(path, title, variable, gcm, rcm, "23234")


def insert_climate_data(path, title, variable, gcm, rcm, size, processing, start, end):
    meta_climate_layer = {}
    meta_climate_layer["title"] = title
    meta_climate_layer["variable_id"] = (
        ClimateVariable.objects.filter(variable_abbr=variable).first().id
    )
    try:
        meta_climate_layer["procesing_method_id"] = (
            ProcessingMethod.objects.filter(name=processing).first().id
        )
    except Exception:
        pass

    meta_climate_layer["local_path"] = path
    meta_climate_layer["file_name"] = title
    meta_climate_layer["climate_dataset_id"] = (
        ClimateModelling.objects.filter(
            modellingBase__project__name_short="CMIP5",
            modellingBase__forcing_global_model__name_short=gcm,
            modellingBase__regional_model__name_short=rcm,
            modellingBase__experiment_id="r1i1p1",
            scenario__name_short="RCP8.5",
        )
        .first()
        .id
    )

    meta_climate_layer["date_begin"] = start + "-01-01"
    meta_climate_layer["date_end"] = end + "-12-31"

    meta_climate_layer["size"] = size
    #####
    meta_climate_layer["progress_id"] = (
        ISOcodelist.objects.filter(identifier="completed").first().id
    )

    meta_climate_layer["abstract"] = "Abstract"
    meta_climate_layer["meta_lineage"] = (
        "The dataset was created by merging the following datasets: XXX."
    )

    meta_climate_layer["status"] = "internal"
    meta_climate_layer["frequency"] = "daily"

    meta_climate_layer["west"] = 10.01
    meta_climate_layer["east"] = 51.81
    meta_climate_layer["south"] = -35.97
    meta_climate_layer["north"] = -5.17

    meta_climate_layer["date_publication"] = "2023-01-01"
    meta_climate_layer["date_creation"] = "2018-01-01"
    meta_climate_layer["date_revision"] = "2018-01-01"

    check_create_climate_layer(meta_climate_layer)


def check_create_climate_layer(meta_climate_layer):
    meta_new = {}
    meta_add = {}

    meta_new["dataset_id"] = meta_climate_layer["climate_dataset_id"]
    meta_new["variable_id"] = meta_climate_layer["variable_id"]
    meta_new["local_path"] = meta_climate_layer["local_path"]
    meta_new["file_name"] = meta_climate_layer["file_name"]
    meta_new["size"] = meta_climate_layer["size"]
    meta_new["frequency"] = meta_climate_layer["frequency"]
    try:
        meta_new["processing_method_id"] = meta_climate_layer["procesing_method_id"]
    except Exception:
        pass
    #  meta_new['satus'] = meta_climate_layer['status']

    # Title
    meta_new["title"] = meta_climate_layer["title"]
    # meta_new['alternative_title'] = meta_climate_layer['alternative_title']
    # topic category
    meta_add["topicCategory"] = ["climatologyMeteorologyAtmosphere"]

    # use tracking id? or chreate new UUID?
    meta_new["identifier"] = uuid.uuid4().hex

    # Country
    # countries = {item.name: item for item in Country.objects.all()}
    # meta['country'] = countries["Germany"]

    meta_new["meta_language"] = "en"

    # Abstract #todo create for LANDSURF and TIPPECC
    meta_new["abstract"] = meta_climate_layer["abstract"]

    # Keywords
    # meta_add = read_keywords(meta_add, df.iloc[i, 8], i)

    # given extent
    meta_new["west"] = meta_climate_layer["west"]
    meta_new["east"] = meta_climate_layer["east"]
    meta_new["south"] = meta_climate_layer["south"]
    meta_new["north"] = meta_climate_layer["north"]

    # time period #todo

    meta_new["date_begin"] = meta_climate_layer["date_begin"]
    meta_new["date_end"] = meta_climate_layer["date_end"]

    # change dates
    if meta_climate_layer["date_creation"]:
        meta_new["date_creation"] = meta_climate_layer["date_creation"]
    if meta_climate_layer["date_publication"]:
        meta_new["date_publication"] = meta_climate_layer["date_publication"]
    if meta_climate_layer["date_revision"]:
        meta_new["date_revision"] = meta_climate_layer["date_revision"]

    # progress
    meta_new["progress_id"] = meta_climate_layer["progress_id"]

    # denominator todo
    # meta_new['denominator'] = "1"

    # meta_new['resolution_distance'] = "0.1"
    # meta_new['resolution_unit'] = "cm"

    # meta_new['dataset_epsg'] = df.iloc[i, 6]

    # meta_add["data_source"] = {}
    # meta_add["data_source"] = df.iloc[i, 4].split(",")

    # Lineage
    # source_link = ""
    # if len(meta_add['data_source']) > 0:
    #    for data_source in meta_add['data_source']:
    # try:
    #         print(data_source.strip())
    #        layer = SourceLayer.objects.get(title__exact=data_source.strip())
    #         source_link = str(
    #              source_link) + " " + layer.title + " (https://geoportal.geodaten.niedersachsen.de/harvest/srv/ger/catalog.search#/metadata/" + str(
    #              layer.identifier) + ")"
    # except Exception as e:
    #     print (str(e))
    meta_new["meta_lineage"] = meta_climate_layer["meta_lineage"]
    # meta_new[
    #     'meta_lineage'] = "Der Datensatz setzt sich aus folgenden Quelldaten zusammen: " + source_link + ". Hinweis: Die Quelldaten werden zu " \
    #                                                                                                      "unterschiedlichen Zeitpunkten aktualisiert und " \
    #                                                                                                      "mit dem jeweiligen Aktualitätsstand in diesem " \
    #                                                                                                      "Datensatz abgebildet. "

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

    # meta_new["meta_file_info"] = df.iloc[i, 14]

    print(meta_add)

    # meta['scope']
    # print(df.iloc[i, 1])
    # print(df.iloc[i, 13])

    # meta_add['point_of_contacts_id'] = [
    #    Contact.objects.get(Q(organisation__contains=str(df.iloc[i, 13]) + ":") & ~Q(organisation__contains=str(df.iloc[i, 13]) + ".")).id]
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
    print("save")
    print(meta_new)

    layer = ClimateLayer(**meta_new)
    layer.save()

    # todo
    # meta_new["data_source"] =
    # if len(meta_add['data_source']) > 0:
    #     for data_source in meta_add['data_source']:
    #         try:
    #             layer.data_source.add(SourceLayer.objects.get(title__exact=data_source.strip()).id)
    #         except Exception as e:
    #             print(str(e))

    layer.topicCategory.clear()
    if len(meta_add["topicCategory"]) > 0:
        for topic_cat in meta_add["topicCategory"]:
            try:
                layer.topicCategory.add(
                    ISOcodelist.objects.get(identifier=topic_cat).id
                )
            except Exception as e:
                print(str(e))

    # layer.inspire_theme.clear()
    # add_inspire_theme(meta_add, layer)

    # layer.layer_keywords.clear()
    # add_keywords(meta_add, layer, "layer")

    # layer.point_of_contacts.clear()
    # for contact in meta_add['point_of_contacts_id']:
    #    try:
    #        layer.point_of_contacts.add(Contact.objects.get(id=contact).id)
    #    except Exception as e:
    #        print(str(e))


#  ConstraintConditionsInline.objects.filter(layer=layer).delete()
#  if meta_add['layer_constraints_limit']:
#      for const_cond in meta_add['layer_constraints_limit']:
#          try:
#              ConstraintConditionsInline(constraints_cond=const_cond, layer=layer).save()
#          except Exception as e:
#              print (e)


def create_seed_data():
    pass
    # initial_fill_iso_codelist('./gmxCodelists.xml')
    # initial_fill_inspire_themes()
    # initial_fill_country()
    # initial_fill_cf_standard_names()
    # initial_seed_climate_contacts()
    # initial_seed_climate()
    # insert_climate_data()
    # test_instet_climate_data()
    ClimateLayer.objects.all().delete()
    #myPath = "/opt/rbis/www/tippecc_data/WITS_regional_bias_corrected"
    #read_and_insert_data(myPath, "Bias corrected")
    #myPath = "/opt/rbis/www/tippecc_data/WITS_regional_not_bias_corrected"
    #read_and_insert_data(myPath, "")
    myPath = "/opt/rbis/www/tippecc_data/WITS_raw"
    read_and_insert_data(myPath, "")
    #myPath = "/opt/rbis/www/tippecc_data/LANDSURF_indictorb"
    #read_and_insert_data(myPath, "")


if __name__ == "__main__":
    import django

    django.setup()
    create_seed_data()
