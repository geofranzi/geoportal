from django.contrib.auth.models import User, Group
from django.db.models import Q
from rest_framework import serializers
from django.contrib.gis.db import models

from layers.models import Layer, ISOcodelist, KeywordInline, Contact, MetadataSerializer
from map.models import Map, MapLayerInline, MapSerializer
from content.models import Country
from geospatial.models import Region


class InspireTheme(models.Model):
    uri = models.CharField(max_length=400, verbose_name="URI")
    name_en = models.CharField(max_length=200, verbose_name="Name (en)")
    name_de = models.CharField(max_length=200, verbose_name="Name (de)")
    definition_en = models.CharField(max_length=1000, verbose_name="Definition (en)")
    definition_de = models.CharField(max_length=1000, verbose_name="Definition (de)")
    topicCategory = models.ForeignKey(ISOcodelist, limit_choices_to={'code_list': "MD_TopicCategoryCode"}, related_name="topicCategory", blank=True, null=True)

    def __str__(self):
        return u"%s" % self.name_en


class InspireThemesSerializer(serializers.ModelSerializer):
    class Meta:
        model = InspireTheme
        fields = ('uri', 'name_en', 'name_de', 'definition_en', 'definition_de', 'topicCategory')

class SourceLayer(Layer):
    internal_contact = models.ForeignKey(Contact, related_name="internal_contact", verbose_name="Internal Contact", blank=True, null=True)
    internal_responsible_city_department = models.ForeignKey(Contact, related_name="city_department",
                                                         limit_choices_to=Q(organisation__startswith="Stadt Hameln"))
    internal_legal_basis = models.TextField(max_length=1000, blank=True, null=True)
    internal_access_constraint = models.TextField(max_length=300, blank=True, null=True)
    internal_comment = models.TextField(max_length=1000, blank=True, null=True)

    internal_pg_table_name = models.TextField(max_length=1000, blank=True, null=True)

    opendata = models.BooleanField(default=False)
    inspireidentified = models.BooleanField(default=False)

    inspire_theme = models.ManyToManyField(InspireTheme, blank=True, related_name="source_inspire_theme")

class InspireDataset(Layer):

    inspire_theme = models.ManyToManyField(InspireTheme, blank=True, related_name="inspire_theme")

    opendata = models.BooleanField(default=False)
    inspireidentified = models.BooleanField(default=False)

    inspire_published = models.BooleanField(default=False)
    inspire_first_publication_date = models.DateTimeField(verbose_name="First publication date",  blank=True, null=True)
    inspire_last_publication_date = models.DateTimeField(verbose_name="Last publication date",  blank=True, null=True)
    processing_new_dataset = models.BooleanField("The content of the source dataset changes after processing", default=False)

    def __str__(self):
        return u"%s" % self.title


class ProcessingInline(models.Model):
    order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=False)
    date = models.DateTimeField(verbose_name="execution date")
    description = models.CharField(max_length=2000)
    input_table = models.CharField(max_length=300)
    output_table = models.CharField(max_length=300)
    output_gml = models.FileField("Output GML", upload_to="GML", null=True, blank=True, help_text="Upload output GML")
    layer = models.ForeignKey(InspireDataset, related_name='layer_processing')

    def __unicode__(self):
        return self.layer.title + " " + str(self.active)

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


class InspireMap(Map):
    inspire_theme = models.ManyToManyField(InspireTheme, blank=True, related_name="inspire_theme_map")

    inspire_wms_published = models.BooleanField(default=False)
    inspire_wms_first_publication_date = models.DateTimeField(verbose_name="First publication date", blank=True, null=True)
    inspire_wms_last_publication_date = models.DateTimeField(verbose_name="Last publication date", blank=True, null=True)

    inspire_wfs_published = models.BooleanField(default=False)
    inspire_wfs_first_publication_date = models.DateTimeField(verbose_name="First publication date", blank=True, null=True)
    inspire_wfs_last_publication_date = models.DateTimeField(verbose_name="Last publication date", blank=True, null=True)

class InspireMetadataSerializer(MetadataSerializer):
    inspire_theme = InspireThemesSerializer(many=True)

    class Meta(MetadataSerializer.Meta):
        model = InspireDataset
        fields = MetadataSerializer.Meta.fields + ( 'inspire_theme', )

class SourceMetadataSerializer(MetadataSerializer):
    inspire_theme = InspireThemesSerializer(many=True)

    class Meta(MetadataSerializer.Meta):
        model = SourceLayer
        fields = MetadataSerializer.Meta.fields + ( 'inspire_theme', )


class InspireMapSerializer(MapSerializer):
    inspire_theme = InspireThemesSerializer(many=True)

    class Meta(MapSerializer.Meta):
        model = InspireMap
        fields = MapSerializer.Meta.fields + ('inspire_theme', )
