from django.db import models
from django.contrib.auth.models import User, Group
from django.db.models import Q
from django.http import Http404, HttpResponse
from rest_framework import serializers
from django.contrib.gis.db import models


from layers.models import Layer, ISOcodelist, KeywordInline, Contact, INSPIREthemes, ISOcodelistSerializer
from content.models import Country
from geospatial.models import Region

import json

class InpireLayer(Layer):
    internal_contact = models.ForeignKey(Contact, related_name="internal_contact", verbose_name="Internal Contact", blank=True, null=True)
    internal_responsible_city_department = models.ForeignKey(Contact, related_name="city_department", limit_choices_to= Q(organisation__startswith="Stadt Hameln"))
    internal_legal_basis = models.TextField(max_length=1000, blank=True, null=True)
    internal_access_constraint = models.TextField(max_length=300, blank=True, null=True)
    inspireidentified = models.BooleanField(default=False)
    inspire_title = models.TextField(max_length=500, blank=True, null=True)
    inspire_abstract =  models.TextField(max_length=1000, blank=True, null=True)
    inspire_epsg = models.IntegerField("EPSG code from the transformed dataset", blank=True, null=True, help_text="Just the projection code/number")
    inspire_theme = models.ManyToManyField(INSPIREthemes, blank=True, related_name="inspire_theme")
    processing_new_dataset = models.BooleanField("The content of the source dataset changes after processing", default=False)

    def __str__(self):
        return u"%s" % (self.identifier)


class ProcessingInline(models.Model):
    order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=False)
    date = models.DateTimeField(verbose_name="execution date")
    description = models.CharField(max_length=2000)
    input_table =  models.CharField(max_length=300)
    output_table =  models.CharField(max_length=300)
    layer = models.ForeignKey(InpireLayer, related_name='layer_processing')

    def __unicode__(self):
        return self.layer.inspire_title + " " + str(self.active)

    def save(self, *args, **kwargs):
        if self.active:
            try:
                temp = ProcessingInline.objects.get(active=True)
                if self != temp:
                    temp.active = False
                    temp.save()
            except ProcessingInline.DoesNotExist:
                pass
        super(ProcessingInline, self).save(*args, **kwargs)

    class Meta:
        ordering = ['order']


class InspireMap(models.Model):
    coordination_contact = models.ForeignKey(Contact, related_name="coordination_contact", verbose_name="Coordintion", blank=True, null=True)
    data_contact = models.ForeignKey(Contact, related_name="data_contact", verbose_name="Data contact", blank=True, null=True)
    service_contact = models.ForeignKey(Contact, related_name="service_contact", verbose_name="Service Contact", blank=True, null=True)
    metadata_contact = models.ForeignKey(Contact, related_name="metadata_contact", verbose_name="Metadata Contact", blank=True, null=True)
    ows_contact = models.ForeignKey(Contact, related_name="wms_contact", verbose_name="WMS Contact", blank=True, null=True)
    ows_title_de = models.CharField(max_length=200, null=True, blank=True)
    ows_title_en = models.CharField(max_length=200, null=True, blank=True)
    ows_abstract_de = models.CharField(max_length=2000, null=True, blank=True)
    ows_abstract_en = models.CharField(max_length=2000, null=True, blank=True)
    ows_rootlayer_title_de =models.CharField(max_length=200, null=True, blank=True)
    ows_rootlayer_abstract_en = models.CharField(max_length=2000, null=True, blank=True)
    ows_srs = models.CharField(max_length=200, null=True, blank=True, default="EPSG:3857,EPSG:4258,EPSG:4326,EPSG:3034,EPSG:3035,EPSG:25832,EPSG:31467")
    ows_languages = models.CharField(max_length=200, null=True, blank=True, default="ger", help_text="Add more languages separated by Comma e.g. ger, eng")
    ows_enable_request =  models.CharField(max_length=200, null=True, blank=True, default="*", help_text="GetCapabilities, GetMap, GetFeatureInfo and GetLegendGraphic. A ”!” in front of a request will disable the request. “*” enables all requests.")
    inspire_theme = models.ManyToManyField(INSPIREthemes, blank=True, related_name="inspire_theme_map")


   # wms_rootlayer_keywordlist =
   # keyword model here (warn if one is missing from linked layer)

class KeywordMapInline(models.Model):
    order = models.PositiveIntegerField(default=0)
    keyword = models.CharField(max_length=200)
    thesaurus_name = models.CharField(max_length=300, blank=True, null=True)
    thesaurus_date = models.DateField(blank=True, null=True, verbose_name="Thesaurus publication date")
    thesaurus_date_type_code_code_value = models.ForeignKey(ISOcodelist,limit_choices_to={'code_list': "CI_DateTypeCode"},blank=True, null=True, related_name="map_thesaurus_date_type_code_code_value")
    layer = models.ForeignKey(InspireMap, related_name='layer_keywords')

    def __str__(self):
        return self.keyword

class KeywordInlineSerializer(serializers.ModelSerializer):
    thesaurus_date_type_code_code_value = ISOcodelistSerializer(read_only=True)

    class Meta:
        model = KeywordInline
        fields = ('keyword', 'thesaurus_name', 'thesaurus_date', 'thesaurus_date_type_code_code_value')

class MapStyle(models.Model):
    name = models.CharField(max_length=400)
    style_def= models.CharField(max_length=2000, null=True, blank=True)

    def __unicode__(self):
        return self.name

class InspireMapLayer(models.Model):
    order = models.PositiveIntegerField(default=0)
    ows_group_title_de = models.CharField(max_length=200, null=True, blank=True)
    ows_group_title_en = models.CharField(max_length=200, null=True, blank=True)
    ows_group_abstract_de = models.CharField(max_length=2000, null=True, blank=True)
    ows_group_abstract_en = models.CharField(max_length=2000, null=True, blank=True)

    ows_layer_title_de = models.CharField(max_length=200, null=True, blank=True)
    ows_layer_title_en = models.CharField(max_length=200, null=True, blank=True)
    ows_layer_abstract_de= models.CharField(max_length=2000, null=True, blank=True)
    ows_layer_abstract_en= models.CharField(max_length=2000, null=True, blank=True)

    wms_layer_visibility_from = models.IntegerField(verbose_name="Visibility from", blank=True, null=True, help_text="Lower value")
    wms_layer_visibility_to = models.IntegerField(verbose_name="Visibility to", blank=True, null=True, help_text="Higher value")

    wms_layer_style = models.ForeignKey(MapStyle, related_name="layer_style")
    ows_enable_request =  models.CharField(max_length=200, null=True, blank=True, default="*", help_text="GetCapabilities, GetMap, GetFeatureInfo and GetLegendGraphic. A ”!” in front of a request will disable the request. “*” enables all requests.")

    def __unicode__(self):
        return self.ows_group_title_de + " " + self.ows_group_title_en

    class Meta:
        ordering = ['order']




