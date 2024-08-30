import urllib
from urllib.error import (HTTPError, URLError,)

# from django.contrib.auth.models import (Group, User,)
from django.contrib.gis.db import models
from django.db.models import Q
from django.utils.safestring import mark_safe
from rest_framework import serializers

# from content.models import Country
# from geospatial.models import Region
from layers.models import (Contact, ISOcodelist, Layer, MetadataSerializer,)
from map.models import (Map, MapSerializer,)


class InspireTheme(models.Model):
    uri = models.CharField(max_length=400, verbose_name="URI")
    name_en = models.CharField(max_length=200, verbose_name="Name (en)")
    name_de = models.CharField(max_length=200, verbose_name="Name (de)")
    definition_en = models.CharField(max_length=1000, verbose_name="Definition (en)")
    definition_de = models.CharField(max_length=1000, verbose_name="Definition (de)")
    topicCategory = models.ForeignKey(ISOcodelist, limit_choices_to={'code_list': "MD_TopicCategoryCode"},
                                      related_name="topicCategory", on_delete=models.PROTECT, blank=True, null=True)

    def __str__(self):
        return u"%s" % self.name_en


class InspireThemesSerializer(serializers.ModelSerializer):
    class Meta:
        model = InspireTheme
        fields = ('uri', 'name_en', 'name_de', 'definition_en', 'definition_de', 'topicCategory')


class InspireHVD(models.Model):
    uri = models.CharField(max_length=400, verbose_name="URI")
    name_en = models.CharField(max_length=200, verbose_name="Name (en)")
    name_de = models.CharField(max_length=200, verbose_name="Name (de)")

    def __str__(self):
        return u"%s" % self.name_en


class InspireHVDSerializer(serializers.ModelSerializer):
    class Meta:
        model = InspireHVD
        fields = ('uri', 'name_en', 'name_de')


class SourceLayer(Layer):
    internal_contact = models.ForeignKey(Contact, related_name="internal_contact", verbose_name="Internal Contact",
                                         on_delete=models.PROTECT, blank=True, null=True)
    internal_responsible_city_department = models.ForeignKey(Contact, related_name="city_department",
                                                             limit_choices_to=Q(organisation__startswith="Stadt Hameln"),
                                                             on_delete=models.PROTECT)
    internal_legal_basis = models.TextField(max_length=1000, blank=True, null=True)
    internal_access_constraint = models.TextField(max_length=300, blank=True, null=True)
    internal_comment = models.TextField(max_length=1000, blank=True, null=True)

    internal_pg_table_name = models.TextField(max_length=1000, blank=True, null=True)

    opendata = models.BooleanField(default=False)
    inspireidentified = models.BooleanField(default=False)

    inspire_theme = models.ManyToManyField(InspireTheme, blank=True, related_name="source_inspire_theme")

    def check_csw_published(self):
        return mark_safe('GDI-DE: <a href="https://gdk.gdi-de.org/gdi-de/srv/ger/catalog.search#/metadata/%s" target="_blank" >%s</a> GDI-NI: '
                         '<a href="http://geoportal.geodaten.niedersachsen.de/harvest/srv/api/records/%s" target="_blank" >show</a>'
                         % (self.identifier, check_csw_published(self.identifier), self.identifier))

    # check_csw_published.allow_tags = True
    # in Django 2.0 it will be: from django.utils.safestring import mark_safe;  return mark_safe('<image src="%s" />' % obj.image) or format_html()
    # https://docs.djangoproject.com/en/3.0/ref/utils/#django.utils.html.format_html
    check_csw_published.short_description = "GDI-DE"  # Overwrite name for display


class InspireDataset(Layer):
    inspire_theme = models.ManyToManyField(InspireTheme, blank=True, related_name="inspire_theme")
    inspire_hvd = models.ForeignKey(InspireHVD, related_name="inspire_hvd", on_delete=models.PROTECT, blank=True, null=True)

    opendata = models.BooleanField(default=False)
    inspireidentified = models.BooleanField(default=False)

    inspire_published = models.BooleanField(default=False)
    inspire_first_publication_date = models.DateTimeField(verbose_name="First publication date", blank=True, null=True)
    inspire_last_publication_date = models.DateTimeField(verbose_name="Last publication date", blank=True, null=True)
    processing_new_dataset = models.BooleanField("The content of the source dataset changes after processing", default=False)

    def __str__(self):
        return u"%s" % self.title

    def check_csw_published(self):
        """
        Search for ...
        :rtype: object
        """
        return mark_safe('GDI-DE: <a href="https://gdk.gdi-de.org/gdi-de/srv/ger/catalog.search#/metadata/%s" target="_blank" >%s</a> GDI-NI: '
                         '<a href="http://geoportal.geodaten.niedersachsen.de/harvest/srv/api/records/%s" target="_blank" >show</a>'
                         % (self.identifier, check_csw_published(self.identifier), self.identifier))

    # check_csw_published.allow_tags = True
    # in Django 2.0 it will be: from django.utils.safestring import mark_safe;  return mark_safe('<image src="%s" />' % obj.image) or format_html()
    # https://docs.djangoproject.com/en/3.0/ref/utils/#django.utils.html.format_html
    check_csw_published.short_description = "GDI-DE"  # Overwrite name for display


class ProcessingInline(models.Model):
    order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=False)
    date = models.DateTimeField(verbose_name="execution date")
    description = models.CharField(max_length=2000)
    input_table = models.CharField(max_length=300)
    output_table = models.CharField(max_length=300)
    output_gml = models.FileField("Output GML", upload_to="GML", null=True, blank=True, help_text="Upload output GML")
    layer = models.ForeignKey(InspireDataset, related_name='layer_processing', on_delete=models.CASCADE)

    def __unicode__(self):
        return self.layer.title + " " + str(self.active)

    def save(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        """
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
    inspire_hvd = models.ForeignKey(InspireHVD, related_name="inspire_hvd_map", on_delete=models.PROTECT, blank=True, null=True)

    inspire_wms_published = models.BooleanField(default=False)
    inspire_wms_first_publication_date = models.DateTimeField(verbose_name="First publication date", blank=True, null=True)
    inspire_wms_last_publication_date = models.DateTimeField(verbose_name="Last publication date", blank=True, null=True)

    inspire_wfs_published = models.BooleanField(default=False)
    inspire_wfs_first_publication_date = models.DateTimeField(verbose_name="First publication date", blank=True, null=True)
    inspire_wfs_last_publication_date = models.DateTimeField(verbose_name="Last publication date", blank=True, null=True)

    def check_csw_published(self):
        """

        :return:
        """
        return mark_safe('GDI-DE: <a href="https://gdk.gdi-de.org/gdi-de/srv/ger/catalog.search#/metadata/%s" target="_blank" >%s</a> GDI-NI: <a '
                         'href="http://geoportal.geodaten.niedersachsen.de/harvest/srv/api/records/%s" target="_blank" >show</a>'
                         % (self.service_identifier, check_csw_published(self.service_identifier), self.service_identifier))

    # check_csw_published.allow_tags = True
    # in Django 2.0 it will be: from django.utils.safestring import mark_safe;  return mark_safe('<image src="%s" />' % obj.image) or format_html()
    # https://docs.djangoproject.com/en/3.0/ref/utils/#django.utils.html.format_html
    check_csw_published.short_description = "GDI-DE"  # Overwrite name for display


class InspireMetadataSerializer(MetadataSerializer):
    inspire_theme = InspireThemesSerializer(many=True)
    inspire_hvd = InspireHVDSerializer(read_only=True)

    class Meta(MetadataSerializer.Meta):
        model = InspireDataset
        fields = MetadataSerializer.Meta.fields + ('inspire_theme', 'inspire_hvd')


class SourceMetadataSerializer(MetadataSerializer):
    inspire_theme = InspireThemesSerializer(many=True)
    inspire_hvd = InspireHVDSerializer(read_only=True)

    class Meta(MetadataSerializer.Meta):
        model = SourceLayer
        fields = MetadataSerializer.Meta.fields + ('inspire_theme', 'inspire_hvd')


class InspireMapSerializer(MapSerializer):
    inspire_theme = InspireThemesSerializer(many=True)
    inspire_hvd = InspireHVDSerializer(read_only=True)

    class Meta(MapSerializer.Meta):
        model = InspireMap
        fields = MapSerializer.Meta.fields + ('inspire_theme', 'inspire_hvd')


def check_csw_published(identifier):
    # url = "http://geoportal.geodaten.niedersachsen.de/harvest/srv/api/records/%s" % self.identifier
    url = "https://gdk.gdi-de.org/geonetwork/srv/api/0.1/records/%s" % identifier  # GDi-DE API https://gdk.gdi-de.org/gdi-de/doc/api/#/records/getRecord
    print(url)
    try:
        urllib.request.urlopen(url)
    except HTTPError as e:
        # do something
        print('Error code: ', e.code)
        if (e.code == 404):
            status = "offline / not published"
        else:
            status = "unkown"
    except URLError as e:
        # do something
        print('Reason: ', e.reason)
    else:
        # do something
        print('good!')
        status = "OK"
    return status
