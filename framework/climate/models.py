from django.db import models

from layers.models import (Contact, ISOcodelist, KeywordInline, Layer,)

from .search_es import ClimateDatasetsIndex


class ClimateModel(models.Model):
    TYPE = ("Global", "Global"), ("Regional", "Regional"), ("Local", "Local"), ("Other", "Other"), ("", "None")
    DEFAULT_TYPE = "None"
    name_short = models.CharField(max_length=255, unique=True)
    name_long = models.CharField(max_length=500, blank=True, null=True)
    code = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    web_url = models.TextField(blank=True, null=True)
    version = models.CharField(max_length=10, blank=True, null=True)
    versionDate = models.DateField(blank=True, null=True)
    publisher = models.ForeignKey(Contact, related_name="Publisher", blank=True, null=True, on_delete=models.PROTECT)
    type = models.CharField(max_length=255, choices=TYPE, default=DEFAULT_TYPE, blank=True, null=True)  # Global, Regional, etc.

    # semantic url

    def __str__(self):
        if self.version:
            return self.name_short + "_" + str(self.version)
        else:
            return self.name_short

    def __init__(self, *args, **kwargs):
        super(ClimateModel, self).__init__(*args, **kwargs)
        self.DEFAULT_TYPE = None
        if not self.pk and not self.type:
            self.type = self.DEFAULT_TYPE


# Cordex, EuroCORDEX, etc.
class GlobalClimateModel(ClimateModel):
    DEFAULT_TYPE = "Global"
    pass


# REMO, WRF, etc.
class RegionalClimateModel(ClimateModel):
    DEFAULT_TYPE = "Regional"
    pass


# rcp26, rcp45, rcp60, rcp85, historical, etc.
class ClimateChangeScenario(models.Model):
    TYPE = ("RCP", "RCP"), ("SSP", "SSP"), ("Other", "Other"), ("", "None")
    name_short = models.CharField(max_length=255, unique=True)
    name_long = models.CharField(max_length=500, blank=True, null=True)
    code = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    web_url = models.TextField(max_length=500, blank=True, null=True)
    type = models.CharField(max_length=255, choices=TYPE, blank=True, null=True)  # RCP, SSP, etc.

    def __str__(self):
        return self.name_short


# CMIP5, CMIP6, etc.
class CoupledModelIntercomparisonProject(models.Model):
    name_short = models.CharField(max_length=255, unique=True)
    name_long = models.CharField(max_length=500, blank=True, null=True)
    code = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    web_url = models.TextField(max_length=500, blank=True, null=True)

    def __str__(self):
        return self.name_short


class CfStandardNames(models.Model):
    entry_id = models.CharField(max_length=255, unique=True)
    canonical_units = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    grib = models.CharField(max_length=255, blank=True, null=True)
    amip = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return str(self.entry_id) + " (" + str(self.canonical_units) + ")"


class ProcessingMethod(models.Model):
    TYPE = ("Bias Correction", "Bias Correction"), ("Downscaling", "Downscaling"), ("Other", "Other"), ("", "None")
    name = models.CharField(max_length=255, unique=True)
    type = models.CharField(choices=TYPE, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    ref_url = models.TextField(max_length=500, blank=True, null=True)
    ref_citation = models.TextField(max_length=500, blank=True, null=True)


class ClimatePeriods(models.Model):
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.start_date.__format__("Y") + " - " + self.end_date.__format__("Y")


class ClimateProjections(models.Model):
    name = models.CharField(max_length=255, unique=True)  # 20 years period
    ref_period = models.ManyToManyField(ClimatePeriods, related_name="ref_period_period", verbose_name="Reference Period(s)", blank=True)
    proj_period = models.ManyToManyField(ClimatePeriods, related_name="proj_period_period", verbose_name="Projection Period(s)", blank=True)

    def __str__(self):
        return self.name


class ClimateModellingBase(models.Model):
    project = models.ForeignKey(CoupledModelIntercomparisonProject, verbose_name="Coupled Model Intercomparison Project", blank=True, null=True,
                                on_delete=models.PROTECT)
    forcing_global_model = models.ForeignKey(GlobalClimateModel, verbose_name="Global Climate Model", blank=True, null=True, on_delete=models.PROTECT)
    regional_model = models.ForeignKey(RegionalClimateModel, verbose_name="Regional Climate Model", blank=True, null=True, on_delete=models.PROTECT)
    experiment_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return str(self.project) + "_" + str(self.forcing_global_model) + "_" + str(self.regional_model) + "_" + str(self.experiment_id)


class ClimateModelling(models.Model):
    modellingBase = models.ForeignKey(ClimateModellingBase, verbose_name="Modelling Base", on_delete=models.PROTECT)
    scenario = models.ForeignKey(ClimateChangeScenario, verbose_name="Scenario", blank=True, null=True, on_delete=models.PROTECT)
    ref_and_proj_periods = models.ForeignKey(ClimatePeriods, verbose_name="Reference and Projection Period(s)", blank=True, null=True, on_delete=models.PROTECT)
    bias_correction_method = models.ForeignKey(ProcessingMethod, verbose_name="Bias Correction Method", blank=True, null=True, on_delete=models.PROTECT)

    def __str__(self):
        return str(self.modellingBase) + "_" + str(self.scenario) + "_" + str(self.ref_and_proj_periods) + "_" + str(self.bias_correction_method)


class ClimateVariable(models.Model):
    TYPE = ("raw", ""), ("indicator", "indicator")
    variable_abbr = models.CharField(max_length=20, blank=True, null=True)
    variable_name = models.CharField(max_length=255, blank=True, null=True)
    variable_standard_name_cf = models.ForeignKey(CfStandardNames, related_name="Variable", blank=True, null=True, on_delete=models.PROTECT)
    variable_unit = models.CharField(max_length=255, blank=True, null=True)
    variable_cell_methods = models.CharField(max_length=255, blank=True, null=True)
    variable_description = models.TextField(blank=True, null=True)
    variable_type = models.CharField(max_length=20, choices=TYPE, default="raw", blank=True, null=True)
    variable_ref_url = models.TextField(max_length=500, blank=True, null=True)

    def __str__(self):
        return str(self.variable_name) + " (" + str(self.variable_abbr) + ")" + " [" + str(self.variable_unit) + "]" + " [" + str(
            self.variable_standard_name_cf.entry_id) + "]" + " [" + str(self.variable_type) + "]"


class ClimateLayer(Layer):  # resolution use Layer
    FREQUENCY = ("daily", "daily"), ("monthly", "monthly"), ("yearly", "yearly")
    STATUS = ("planned", "planned"), ("internal", "internal"), ("public", "public"), ("external", "external")
    dataset = models.ForeignKey(ClimateModelling, verbose_name="Climate Dataset", on_delete=models.PROTECT)
    frequency = models.CharField(max_length=20, choices=FREQUENCY, blank=True, null=True)
    cf_version = models.CharField(max_length=20, blank=True, null=True)
    processing_method = models.ForeignKey(ProcessingMethod, verbose_name="Processing Method", blank=True, null=True, on_delete=models.PROTECT)
    variable = models.ForeignKey(ClimateVariable, verbose_name="Climate Variable", blank=True, null=True, on_delete=models.PROTECT)
    variable_name_in_file = models.CharField(max_length=255, blank=True, null=True)

    local_path = models.TextField(blank=True, null=True)
    file_name = models.CharField(max_length=500, blank=True, null=True)
    size = models.FloatField(blank=True, null=True, verbose_name='Size (GB)')
    status = models.CharField(max_length=20, choices=STATUS, blank=True, null=True)

    tracking_id = models.CharField(max_length=255, blank=True, null=True)
    tracking_base_url = models.CharField(max_length=255, blank=True, null=True)
    source_path = models.CharField(max_length=255, blank=True, null=True)

    @property
    def download_path(self):
        if self.local_path is not None and self.file_name is not None:
            return self.local_path.replace("/opt/rbis/www/", "https://leutra.geogr.uni-jena.de/") + "/" + self.file_name
        else:
            return ""

    def __str__(self):
        return str(self.dataset) + " - " + str(self.dataset.scenario) + " (" + str(self.variable.variable_abbr) + ")" + " [" + str(self.frequency) + "]"

    def indexing(self):

        topic_cats = []
        for topic_cat in self.topicCategory.all():
            res = ISOcodelist.objects.get(pk=topic_cat.id)
            topic_cats.append(res.identifier)

        keywords = []
        for keyword in KeywordInline.objects.filter(layer=self.id):
            keywords.append(keyword.keyword)

        contact_name = []
        contact_org = []
        for contact in self.point_of_contacts.all():
            res = Contact.objects.get(pk=contact.id)
            contact_name.append(contact.first_name + " " + contact.last_name)
            contact_org.append(contact.organisation)
        for meta_contact in self.meta_contacts.all():
            res = Contact.objects.get(pk=contact.id)
            contact_name.append(contact.first_name + " " + contact.last_name)
            contact_org.append(contact.organisation)

        extent = {
            "type": "Polygon",
            "coordinates": [[[self.west, self.north], [self.east, self.north], [self.east, self.south], [self.west, self.south], [self.west, self.north]]]
        }

        obj = ClimateDatasetsIndex(
            meta={'id': self.id},
            title=self.title,
            variable_standard_name_cf=self.variable.variable_standard_name_cf.entry_id,
            variable_name=self.variable.variable_name,
            variable_name_in_file=self.variable_name_in_file,
            variable_abbr=self.variable.variable_abbr,
            description=self.abstract,
            topiccat=topic_cats,
            keywords=keywords,
            contact_name=contact_name,
            contact_org=contact_org,
            date_begin=self.date_begin,
            date_end=self.date_end,
            lineage=self.meta_lineage,
            geom=extent,
            gcm=self.dataset.modellingBase.forcing_global_model.name_short,
            rcm=self.dataset.modellingBase.regional_model.name_short,
            local_path=self.local_path,
            file_name=self.file_name,
            size=self.size,
            status=self.status,
            tracking_id=self.tracking_id,
            tracking_base_url=self.tracking_base_url,
            source_path=self.source_path,
            variable_type=self.variable.variable_type,
            variable_unit=self.variable.variable_unit,
            variable_cell_methods=self.variable.variable_cell_methods,
            variable_description=self.variable.variable_description,
            variable_ref_url=self.variable.variable_ref_url,
            frequency=self.frequency,
            cf_version=self.cf_version,
            dataset=str(self.dataset),

        )
        print(obj)
        obj.save()
        return obj.to_dict(include_meta=True)


class ProvenanceInline(models.Model):
    RELATION_TYPE = ("isPartOf", "isPartOf"), ("isVersionOf", "isVersionOf"), ("isBasedOn", "isBasedOn"), ("isComposedOf", "isComposedOf"), (
        "isDescribedBy", "isDescribedBy"), ("isDerivedFrom", "isDerivedFrom"), ("isFormatOf", "isFormatOf"), ("isIdenticalTo", "isIdenticalTo"), (
                        "isMetadataFor", "isMetadataFor"), ("isNextVersionOf", "isNextVersionOf"), ("isPreviousVersionOf", "isPreviousVersionOf"), (
                        "isSourceOf", "isSourceOf"), ("isSupplementTo", "isSupplementTo"), ("isSupplementedBy", "isSupplementedBy"), (
                        "isVariantFormOf", "isVariantFormOf"), ("references", "references"), ("replaces", "replaces"), ("requires", "requires"), (
                        "source", "source")
    relation_type = models.CharField(max_length=20, choices=RELATION_TYPE, blank=True, null=True)
    target = models.ForeignKey(ClimateLayer, related_name="Target", blank=True, null=True, on_delete=models.PROTECT)
    climate_layer = models.ForeignKey(ClimateLayer, related_name="Climate_Layer", blank=True, null=True, on_delete=models.PROTECT)

    def __str__(self):
        return self.relation_type + " " + self.target.name
