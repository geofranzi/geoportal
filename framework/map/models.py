from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from webgis import settings


from layers.models import Contact, ContactSerializer, ISOcodelist, ISOcodelistSerializer, KeywordInline, Layer, LayerSerializer  # isort:skip


class MapLayerStyle(models.Model):
    name = models.CharField(max_length=400)
    description = models.CharField(max_length=4000, null=True, blank=True)
    template_file = models.FilePathField("Template file",
                                         path=settings.TEMPLATES[0]['DIRS'][0]+'/sld', match=".*\.xml", max_length=1000, blank=True, null=True)  # noqa: W605

    def __unicode__(self):
        return self.name


class Map(models.Model):
    distributor_contact = models.ForeignKey(Contact, related_name="coordination_contact", verbose_name=_("Coordination"), on_delete=models.PROTECT, blank=True, null=True)
    metadata_contact = models.ForeignKey(Contact, related_name="metadata_contact", verbose_name=_("Metadata contact"), on_delete=models.PROTECT, blank=True, null=True)
    service_contact = models.ForeignKey(Contact, related_name="service_contact", verbose_name=_("Service contact"), on_delete=models.PROTECT, blank=True, null=True)

    service_name = models.CharField(max_length=200, verbose_name=_("WMS name"), null=True, blank=True)
    service_abstract = models.CharField(max_length=2000, verbose_name=_("WMS abstract"), null=True, blank=True)
    service_publication_date = models.DateField(verbose_name=_("WMS publication date"), blank=True, null=True)
    service_identifier = models.CharField(max_length=200, verbose_name=_("WMS UUID"), null=True, blank=True)

    download_name = models.CharField(max_length=200, verbose_name=_("Download nme"), null=True, blank=True)
    download_abstract = models.CharField(max_length=2000, verbose_name=_("Download abstract"), null=True, blank=True)
    download_publication_date = models.DateField(verbose_name=_("Download publication date"), blank=True, null=True)
    download_type = models.CharField(max_length=200, default="WFS", verbose_name=_("Download type"), null=True, blank=True)
    download_secure = models.BooleanField(verbose_name=_("Secure download"), default=False)
    download_identifier = models.CharField(max_length=200, verbose_name=_("Download UUID"), null=True, blank=True)

    # Geographic Extent
    west = models.FloatField("BBOX west coordinate", default=settings.DEFAULT_EXTENT_WEST, help_text="e.g. -180")
    east = models.FloatField("BBOX east coordinate", default=settings.DEFAULT_EXTENT_EAST, help_text="e.g. 180")
    north = models.FloatField("BBOX north coordinate", default=settings.DEFAULT_EXTENT_NORTH, help_text="e.g. 90")
    south = models.FloatField("BBOX south coordinate", default=settings.DEFAULT_EXTENT_SOUTH, help_text="e.g. -90")
    geo_description = models.CharField("Location description", max_length=200, blank=True, null=True)

    ows_url_name = models.CharField(max_length=200, verbose_name=_("Identifier name"), null=True, blank=True,
                                    help_text="Used for name of Mapfile, SLD and short URL")

    ows_contact = models.ForeignKey(Contact, related_name="wms_contact", verbose_name=_("WMS contact"), on_delete=models.PROTECT, blank=True, null=True)
    ows_title_de = models.CharField(max_length=200, null=True, blank=True)
    ows_title_en = models.CharField(max_length=200, null=True, blank=True)
    ows_abstract_de = models.CharField(max_length=2000, null=True, blank=True)
    ows_abstract_en = models.CharField(max_length=2000, null=True, blank=True)
    ows_style_name = models.CharField(max_length=2000, null=True, blank=True)
    ows_rootlayer_title_de = models.CharField(max_length=200, null=True, blank=True)
    ows_rootlayer_title_en = models.CharField(max_length=200, null=True, blank=True)
    ows_rootlayer_abstract_en = models.CharField(max_length=2000, null=True, blank=True)
    ows_rootlayer_abstract_de = models.CharField(max_length=2000, null=True, blank=True)
    ows_srs = models.CharField(max_length=200, null=True, blank=True, default="EPSG:3857,EPSG:4258,EPSG:4326,EPSG:3034,EPSG:3035,EPSG:25832,EPSG:31467")
    ows_languages = models.CharField(max_length=200, null=True, blank=True, default="ger", help_text="Add more languages separated by Comma e.g. ger, eng")
    ows_enable_request = models.CharField(max_length=200, null=True, blank=True, default="*",
                                          help_text="GetCapabilities, GetMap, GetFeatureInfo and GetLegendGraphic. A ”!” in front of a request will disable "
                                                    "the request. “*” enables all requests.")

    def check_keywords(self):
        map_layers = self.map_layer.all()
        map_keywords = self.map_keywords.all()
        missing_keywords = []
        for layer in map_layers:
            keywords = layer.map_layer.layer_keywords.all()
            for keyword in keywords:
                if keyword.keyword not in map_keywords.values(keyword):
                    missing_keywords.append(keyword)

        return missing_keywords

    def get_wms_url(self):
        return settings.BASE_URL + self.ows_url_name

    def __unicode__(self):
        return self.service_name

    def full_name(self):
        return '%s<br>%s<br>Map: %s (%s)' % (self.service_name, self.download_name, self.ows_rootlayer_title_de, self.ows_rootlayer_title_en)

    full_name.allow_tags = True  # in Django 2.0 it will be: return mark_safe('<image src="%s" />' % obj.image) or format_html()
    # https://docs.djangoproject.com/en/3.0/ref/utils/#django.utils.html.format_html
    full_name.short_description = "WMS & WFS Dienste"  # Overwrite name for display


class OnlineResourceMapInline(models.Model):
    order = models.PositiveIntegerField(default=0)
    linkage = models.CharField(max_length=400, blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    protocol = models.CharField(max_length=200, blank=True, null=True)
    description = models.CharField(max_length=500, blank=True, null=True)
    function = models.ForeignKey(ISOcodelist, limit_choices_to={'code_list': 'CI_OnLineFunctionCode'}, on_delete=models.PROTECT, blank=True, null=True)
    map = models.ForeignKey(Map, related_name='map_online_resource', on_delete=models.CASCADE)

    def __str__(self):
        return self.linkage


class OnlineResourceMapInlineSerializer(serializers.ModelSerializer):
    function = ISOcodelistSerializer(read_only=True)

    class Meta:
        model = OnlineResourceMapInline
        fields = ('linkage', 'name', 'protocol', 'description', 'function')


class ConstraintLimitMapInline(models.Model):
    order = models.PositiveIntegerField(default=0)
    constraints_limit = models.CharField("Limitations on public access", max_length=400, blank=True, null=True)
    map = models.ForeignKey(Map, related_name='map_constraints_limit', on_delete=models.CASCADE)

    def __str__(self):
        return self.constraints_limit


class ConstraintLimitMapInlineSerializer(serializers.ModelSerializer):

    class Meta:
        model = ConstraintLimitMapInline
        fields = ('constraints_limit', )


class ConstraintConditionsMapInline(models.Model):
    order = models.PositiveIntegerField(default=0)
    constraints_cond = models.CharField("Conditions applying to access and use", max_length=400, blank=True, null=True)
    map = models.ForeignKey(Map, related_name='map_constraints_cond', on_delete=models.CASCADE)

    def __str__(self):
        return self.constraints_cond


class ConstraintConditionsMapInlineSerializer(serializers.ModelSerializer):

    class Meta:
        model = ConstraintConditionsMapInline
        fields = ('constraints_cond', )


class ConformityMapInline(models.Model):
    order = models.PositiveIntegerField(default=0)
    title = models.CharField("Conformity", max_length=400, blank=True, null=True)
    date = models.DateField(blank=True, null=True, verbose_name="Date")
    date_type = models.ForeignKey(ISOcodelist, limit_choices_to={'code_list': "CI_DateTypeCode"}, on_delete=models.PROTECT, blank=True, verbose_name="Date type")
    map = models.ForeignKey(Map, related_name='map_conformity', on_delete=models.CASCADE)

    def __str__(self):
        return self.title


class ConformityMapInlineSerializer(serializers.ModelSerializer):
    date_type = ISOcodelistSerializer(read_only=True)

    class Meta:
        model = ConformityMapInline
        fields = ('title', 'date', 'date_type')


class KeywordMapInline(models.Model):
    order = models.PositiveIntegerField(default=0)
    keyword = models.CharField(max_length=200)
    uri = models.CharField(max_length=400, verbose_name="URI", blank=True, null=True)
    thesaurus_name = models.CharField(max_length=300, blank=True, null=True)
    thesaurus_date = models.DateField(blank=True, null=True, verbose_name=_("Thesaurus publication date"))
    thesaurus_date_type_code_code_value = models.ForeignKey(ISOcodelist, limit_choices_to={'code_list': "CI_DateTypeCode"}, on_delete=models.PROTECT, blank=True, null=True,
                                                            related_name="map_thesaurus_date_type_code_code_value")
    map = models.ForeignKey(Map, related_name='map_keywords', on_delete=models.CASCADE)

    def __str__(self):
        return self.keyword


class KeywordMapInlineSerializer(serializers.ModelSerializer):
    thesaurus_date_type_code_code_value = ISOcodelistSerializer(read_only=True)

    class Meta:
        model = KeywordInline
        fields = ('keyword', 'uri', 'thesaurus_name', 'thesaurus_date', 'thesaurus_date_type_code_code_value')


class MapGroup(models.Model):
    ows_group_title_de = models.CharField(max_length=200, null=True, blank=True)
    ows_group_title_en = models.CharField(max_length=200, null=True, blank=True)
    ows_group_abstract_de = models.CharField(max_length=2000, null=True, blank=True)
    ows_group_abstract_en = models.CharField(max_length=2000, null=True, blank=True)

    def __str__(self):
        if self.ows_group_title_de:
            return u"%s" % self.ows_group_title_de
        if self.ows_group_title_en:
            return u"%s" % self.ows_group_title_en


class MapLayerInline(models.Model):
    order = models.PositiveIntegerField(default=0)

    ows_group = models.ForeignKey(MapGroup, related_name='map_group', on_delete=models.PROTECT, null=True, blank=True)

    ows_layer_title_de = models.CharField(max_length=200, null=True, blank=True)
    ows_layer_title_en = models.CharField(max_length=200, null=True, blank=True)
    ows_layer_abstract_de = models.CharField(max_length=2000, null=True, blank=True)
    ows_layer_abstract_en = models.CharField(max_length=2000, null=True, blank=True)

    ows_layer_name = models.CharField(max_length=200, null=True, blank=True)
    wms_layer_min_scale = models.IntegerField(verbose_name=_("Visibility from"), blank=True, null=True, help_text="Lower value")
    wms_layer_max_scale = models.IntegerField(verbose_name=_("Visibility to"), blank=True, null=True, help_text="Higher value")

    ows_geometry_type = models.CharField(max_length=200, null=True, blank=True)
    ows_filter_item = models.CharField(max_length=200, null=True, blank=True)
    ows_filter_value = models.CharField(max_length=200, null=True, blank=True)

    ows_layer_spatial_object_name = models.CharField(max_length=200, null=True, blank=True)
    wms_layer_style_link = models.ForeignKey(MapLayerStyle, on_delete=models.PROTECT, null=True, related_name="layer_style", blank=True)
    ows_enable_request = models.CharField(max_length=200, null=True, blank=True, default="*",
                                          help_text="GetCapabilities, GetMap, GetFeatureInfo and GetLegendGraphic. A "
                                                    "”!” in front of a request will disable the request. “*” enables "
                                                    "all requests.")
    ows_additional_infos = models.CharField(max_length=2000, null=True, blank=True)
    map_layer = models.ForeignKey(Layer, related_name='layer_map', on_delete=models.PROTECT, null=True, blank=True)
    map = models.ForeignKey(Map, related_name='map_layer', on_delete=models.CASCADE)

    def __unicode__(self):
        return self.ows_layer_title_de + " " + self.ows_layer_title_en

    class Meta:
        ordering = ['order']


class MapGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = MapGroup
        fields = ('ows_group_title_de', 'ows_group_title_en', 'ows_group_abstract_de', 'ows_group_abstract_en')


class MapLayerStyleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MapLayerStyle
        fields = ('name', 'description', 'template_file')


class MapLayerInlineSerializer(serializers.ModelSerializer):
    # ows_group = MapGroupSerializer(read_only=True)
    wms_layer_style_link = MapLayerStyleSerializer(read_only=True)
    map_layer = LayerSerializer(read_only=True)

    class Meta:
        model = MapLayerInline
        fields = ('order', 'ows_layer_title_de', 'ows_layer_title_en', 'ows_layer_abstract_de', 'ows_layer_abstract_en',
                  'ows_layer_name', 'wms_layer_min_scale', 'wms_layer_max_scale', 'ows_enable_request',
                  'ows_geometry_type', 'ows_filter_item', 'ows_filter_value', 'ows_additional_infos',
                  'ows_layer_spatial_object_name', 'wms_layer_style_link', 'map_layer')


class MapSerializer(serializers.ModelSerializer):
    coordination_contact = ContactSerializer(read_only=True)
    data_contact = ContactSerializer(read_only=True)
    service_contact = ContactSerializer(read_only=True)
    metadata_contact = ContactSerializer(read_only=True)
    ows_contact = ContactSerializer(read_only=True)
    map_keywords = KeywordMapInlineSerializer(many=True, read_only=True)
    map_layer = MapLayerInlineSerializer(many=True, read_only=True)
    map_constraints_cond = ConstraintConditionsMapInlineSerializer(many=True, read_only=True)
    map_constraints_limit = ConstraintLimitMapInlineSerializer(many=True, read_only=True)
    map_conformity = ConformityMapInlineSerializer(many=True, read_only=True)
    map_online_resource = OnlineResourceMapInlineSerializer(many=True, read_only=True)

    class Meta:
        model = Map
        fields = (
            'coordination_contact', 'data_contact', 'service_contact', 'metadata_contact',
            'service_publication_date', 'service_abstract', 'service_name', 'service_identifier',
            'download_name', 'download_abstract', 'download_publication_date', 'download_type', 'download_secure', 'download_identifier',
            'ows_contact', 'map_keywords', 'ows_url_name', 'ows_title_de', 'ows_title_en', 'ows_abstract_de', 'ows_abstract_en', 'ows_style_name',
            'ows_rootlayer_title_de', 'ows_rootlayer_title_en', 'ows_rootlayer_abstract_de', 'ows_rootlayer_abstract_en',
            'ows_srs', 'ows_languages', 'ows_enable_request', 'ows_url_name', 'map_layer', 'east', 'west', 'south', 'north',
            'map_constraints_cond', 'map_constraints_limit', 'map_conformity', 'map_online_resource')
