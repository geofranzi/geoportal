from urllib.request import urlopen

from django.contrib.auth.models import (Group, User,)
from django.db import models
from django.http import (Http404, HttpResponse,)
from rest_framework import serializers

from webgis import settings


class WorkPackage(models.Model):
    name = models.CharField(max_length=200, blank=True)
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name + " (" + self.title + ")"


# Contact model (referenced 2x in layer model for metadata contact and dataset contact)
class Contact(models.Model):
    title = models.CharField(max_length=200, blank=True)
    first_name = models.CharField(max_length=200, blank=True)
    last_name = models.CharField(max_length=200, blank=True)
    position = models.CharField(max_length=200, blank=True)
    address = models.CharField(max_length=200, blank=True)
    postcode = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=200, blank=True)
    country = models.CharField(max_length=200, blank=True)
    state = models.CharField(max_length=200, blank=True)
    email = models.CharField(max_length=200, blank=True)
    organisation = models.CharField(max_length=200, blank=True)
    organisation_short = models.CharField(max_length=200, blank=True)

    telephone = models.CharField(max_length=200, blank=True)
    fax = models.CharField(max_length=200, blank=True)
    mobile = models.CharField(max_length=200, blank=True)

    website = models.CharField(max_length=200, blank=True)
    organisation_ror = models.CharField(max_length=200, blank=True, null=True)
    person_orcid = models.CharField(max_length=200, blank=True, null=True)
    image = models.ImageField(upload_to='contact/images/', blank=True, null=True)
    work_packages = models.ManyToManyField(WorkPackage, blank=True)
    related_org = models.ForeignKey('self', verbose_name='Related organization', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        if self.first_name != '' or self.last_name != '':
            name = u"%s %s" % (self.first_name, self.last_name)
            if self.organisation != '':
                name = name + " (%s)" % self.organisation
        elif self.organisation != '':
            name = u"%s (%s)" % (self.organisation, self.email)
        elif self.email != '':
            name = self.email
        return name


# Specify a contact serializer for JSON output (used in MetadataSerializer)
class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = (
            'first_name', 'last_name', 'position', 'address', 'postcode', 'city', 'country', 'state', 'email', 'organisation', 'telephone', 'fax', 'mobile',
            'website')


# ISO 19115 Codelists
class ISOcodelist(models.Model):
    identifier = models.CharField(max_length=200)
    description = models.CharField(max_length=500)
    code_list = models.CharField(max_length=200)

    def __str__(self):
        return u"%s" % (self.identifier)


class ISOcodelistSerializer(serializers.ModelSerializer):
    class Meta:
        model = ISOcodelist
        fields = ('identifier',)


# ISO 19115 Codelists

# Layer model to specify visualization layers with metadata information
class Layer(models.Model):
    updated_at = models.DateTimeField(auto_now=True)

    # Overview
    identifier = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    alternative_title = models.CharField(max_length=200, null=True, blank=True)
    title_en = models.CharField(max_length=200, null=True, blank=True)
    abstract = models.TextField()
    abstract_en = models.TextField(null=True, blank=True)
    topicCategory = models.ManyToManyField(ISOcodelist, limit_choices_to={'code_list': "MD_TopicCategoryCode"}, verbose_name="Topic category", default=227)
    SCOPE_ID = 1
    try:
        SCOPE_ID = ISOcodelist.objects.get(identifier="dataset", code_list="MD_ScopeCode").id
    except Exception:
        pass

    scope = models.ForeignKey(ISOcodelist, limit_choices_to={'code_list': "MD_ScopeCode"}, related_name="scope", default=SCOPE_ID, on_delete=models.PROTECT)
    publishable = models.BooleanField(default=False)

    # Vizualiation services
    ogc_link = models.CharField("OGC service URL", max_length=400, blank=True, null=True)
    ogc_layer = models.CharField("Layer name", max_length=200, blank=True, null=True)
    ogc_type = models.CharField("OGC service type", max_length=200,
                                choices=[('WMS', 'WMS'), ('WMTS', 'WMTS'), ('XYZ', 'XYZ'), ('TMS', 'TMS'), ('WFS', 'WFS'), ('Tiled-WFS', 'Tiled-WFS'),
                                         ('GeoJSON', 'GeoJSON'), ('SOS', 'SOS'), ('MapServer', 'MapServer'), ('BingMaps', 'BingMaps'), ('MapQuest', 'MapQuest'),
                                         ('OSM', 'OSM'), ('GoogleMaps', 'GoogleMaps')], default="WMS")
    ogc_time = models.BooleanField("WMS/WMTS Time", default=False, help_text="Time enabled?")
    ogc_imageformat = models.CharField("Image format", max_length=100, blank=True, null=True, help_text="For WMS/WMTS, e.g., image/png, image/jpeg")
    ogc_getfeatureinfo = models.CharField("OGC WMS GetFeatureInfo URL", max_length=200, blank=True, null=True)
    ogc_attribution = models.CharField("Attribution", max_length=255, blank=True, null=True,
                                       help_text="Attribution / Copyright. To add a link use the following syntax (http://www.adress.de, name)")
    ogc_times = models.TextField("Time dimension", blank=True, null=True, help_text="Separated by space/blank character")

    statistic = models.CharField("Layer provide data over time (time series) or area (area statistic)", max_length=20,
                                 choices=[('time', 'Time series'), ('area', 'Area')], default=None, null=True, blank=True)

    # Download services
    downloadable = models.BooleanField(default=False, help_text="Define whether layer can be downloaded")
    download_url = models.CharField("Download URL", max_length=300, null=True, blank=True, help_text="URL for download")
    download_layer = models.CharField("Download layer", max_length=100, null=True, blank=True, help_text="Layername for download url (only wcs)")
    download_type = models.CharField("Download type", max_length=20, choices=[("wcs", "WCS"), ("link", "Link / URL")], blank=True, help_text="")
    download_file = models.FileField("Download file", upload_to='downloads', null=True, blank=True, help_text="Upload file for layer download")
    map_layout_image = models.FileField("Map layout image", upload_to="downloads", null=True, blank=True,
                                        help_text="Upload for a file with the Map Layout Image")
    # download_layer = models.CharField(max_length=200, null=True, blank=True)
    # download_type = models.CharField(max_length=200, choices=[('WCS', 'WCS'), ('WFS', 'WFS'), ('URL', 'URL'), ('SOS', 'SOS')], null=True, blank=True)

    # WMTS settings
    wmts_matrixset = models.CharField("WMTS matrix set", max_length=100, null=True, blank=True)
    wmts_resolutions = models.TextField("WMTS resolutions", blank=True, null=True, help_text="Separated by space/blank character")
    wmts_tilesize = models.IntegerField("WMTS tile size", blank=True, null=True, help_text="e.g., 256 or 512")
    wmts_projection = models.CharField("WMTS projection", max_length=200, blank=True, null=True)
    wmts_multiply = models.BooleanField("WMTS multiply", default=False, help_text="Define wether multiplication is needed for WMTS resolutions")
    wmts_prefix_matrix_ids = models.CharField("WMTS prefix matrix ids", max_length=200, blank=True, null=True)

    # SOS settings
    sos_default_field = models.CharField("SOS default field", max_length=100, null=True, blank=True,
                                         help_text="If blank, the first field from SOS service will be used as default field")

    # Data Quality

    # Dataset description
    dataset_contact_new = models.ForeignKey(Contact, related_name="dataset_contact", verbose_name="Dataset contact - replaced by Dataset point  of contact(s)",
                                            on_delete=models.PROTECT, blank=True, null=True)
    point_of_contacts = models.ManyToManyField(Contact, related_name="meta_point_of_contacts", blank=True, verbose_name="Dataset point of contact(s)")
    date_creation = models.DateField(blank=True, null=True, verbose_name="Dataset creation date")
    date_publication = models.DateField(blank=True, null=True, verbose_name="Dataset publication date")
    date_revision = models.DateField(blank=True, null=True, verbose_name="Dataset revision date")
    language = models.CharField(max_length=200, default="English", blank=True)
    characterset = models.CharField(max_length=200, default="utf8", blank=True, null=True)
    format = models.CharField(max_length=200, blank=True, null=True)
    dataset_epsg = models.IntegerField("EPSG code from the dataset", blank=True, null=True, help_text="Just the projection code/number")
    PROGRESS_ID = 1
    try:
        PROGRESS_ID = ISOcodelist.objects.get(identifier="completed", code_list="MD_ProgressCode").id
    except Exception:
        pass
    progress = models.ForeignKey(ISOcodelist, related_name="progress", limit_choices_to={'code_list': 'MD_ProgressCode'}, default=PROGRESS_ID, blank=True,
                                 null=True, verbose_name="Progress", on_delete=models.PROTECT)

    # Geographic location
    west = models.FloatField("BBOX west coordinate", help_text="e.g. -180")
    east = models.FloatField("BBOX east coordinate", help_text="e.g. 180")
    north = models.FloatField("BBOX north coordinate", help_text="e.g. 90")
    south = models.FloatField("BBOX south coordinate", help_text="e.g. -90")
    geo_description = models.CharField("Location description", max_length=200, blank=True, null=True)

    # Spatial resolution
    SPAT_REPRESENTATION_TYPE_ID = 1
    try:
        SPAT_REPRESENTATION_TYPE_ID = ISOcodelist.objects.get(identifier="vector", code_list="MD_SpatialRepresentationTypeCode").id
    except Exception:
        pass
    spat_representation_type = models.ForeignKey(ISOcodelist, related_name="representation_type",
                                                 limit_choices_to={'code_list': 'MD_SpatialRepresentationTypeCode'}, default=SPAT_REPRESENTATION_TYPE_ID,
                                                 blank=True, null=True, verbose_name="Spatial Representation Type", on_delete=models.PROTECT)
    equi_scale = models.IntegerField("Spatial resolution", blank=True, null=True)
    resolution_distance = models.IntegerField("Resolution", null=True, blank=True)
    resolution_unit = models.CharField("Resolution unit", max_length=30, null=True, blank=True)
    denominator = models.IntegerField("Resolution", null=True, blank=True)

    # Temporal Extent
    date_begin = models.DateField(blank=True, null=True, verbose_name='Begin temporal extent')
    date_end = models.DateField(blank=True, null=True, verbose_name='End temporal extent')

    # Metadata
    meta_contact = models.ForeignKey(Contact, related_name="meta_contact", blank=True, null=True,
                                     verbose_name="Metadata contact - replaced by metadata contacts", on_delete=models.PROTECT)
    meta_contacts = models.ManyToManyField(Contact, related_name="meta_contacts", blank=True, verbose_name="Metadata contact(s)")
    meta_language = models.CharField(max_length=200, default="English", blank=True, verbose_name="Metadata language")
    meta_characterset = models.CharField(max_length=200, default="utf8", blank=True, null=True, verbose_name="Metadata character set")
    meta_date = models.DateField(blank=True, null=True, verbose_name="Metadata date")
    meta_lineage = models.TextField("Lineage information", blank=True, default="")
    meta_file_info = models.TextField("File info e.g. source", null=True, blank=True)
    data_source = models.ManyToManyField("self", verbose_name="Data source", blank=True)

    # Legend
    legend_graphic = models.FileField("Legend graphic file", upload_to='legend', null=True, blank=True)
    legend_url = models.URLField("Legend graphic URL", max_length=400, null=True, blank=True)
    legend_colors = models.TextField("Legend rgb colors", null=True, blank=True)
    legend_info = models.TextField("Legend info", blank=True)

    # Permissions
    auth_perm = models.BooleanField("Access permission", default=False, help_text="Activate access permission for layer")
    auth_users = models.ManyToManyField(User, blank=True, related_name='layer_auth_users', verbose_name="Access users")
    auth_groups = models.ManyToManyField(Group, blank=True, related_name='layer_auth_groups', verbose_name="Access groups")
    download_perm = models.BooleanField("Download permission", default=False, help_text="Activate download permission for layer")
    download_users = models.ManyToManyField(User, blank=True, related_name="layer_download_users")
    download_groups = models.ManyToManyField(Group, blank=True, related_name="layer_download_groups")

    # Zoom
    max_zoom = models.IntegerField("Max Zoom level", null=True, blank=True)
    min_zoom = models.IntegerField("Min Zoom level", null=True, blank=True)

    def __str__(self):
        return u"%s" % (self.identifier)

    @property
    def alternate_title(self):
        return self.title

    def cache(self):
        if self.ogc_type == 'SOS':
            from geojson import (Feature, FeatureCollection, Point, crs, dump,)
            from owslib.etree import etree
            from owslib.sos import SensorObservationService

            # generate Sensor Observation Object
            try:
                sos = SensorObservationService(self.ogc_link, '1.0.0')
            except Exception:
                raise Http404

            # if given offering is not available in this SOS, raise Error
            if self.ogc_layer not in sos.contents:
                raise Http404

            # get features of interest for given offering
            features = sos.contents[self.ogc_layer].features_of_interest

            # retrieve further information about each feature (name, crs, coordinates, first procedure
            featuresAr = []
            i = 1
            for feature in features:
                # request GetFeatureOfInterest from SOS
                f = urlopen(self.ogc_link + '?service=SOS&version=1.0.0&request=GetFeatureOfInterest&FeatureOfInterestId=' + feature)
                sa = f.read()
                f.close()

                # parse returned XML
                root = etree.fromstring(sa)
                name = root.find('{http://www.opengis.net/gml}name').text
                point = root.find('{http://www.opengis.net/sampling/1.0}position').find('{http://www.opengis.net/gml}Point')
                # crsText = point.attrib['srsName']
                procedure = root.find('{http://www.opengis.net/sampling/1.0}relatedObservation').find('{http://www.opengis.net/om/1.0}Observation').find(
                    '{http://www.opengis.net/om/1.0}procedure').attrib['{http://www.w3.org/1999/xlink}href']
                x, y, z = point.find('{http://www.opengis.net/gml}coordinates').text.split(',')

                sensor = sos.describe_sensor(procedure=procedure, outputFormat='text/xml;subtype="sensorML/1.0.1"')
                sensorRoot = etree.fromstring(sensor)
                try:
                    description = sensorRoot[0][0][0].text
                except Exception:
                    description = name

                # create new geometry and feature object from geojson package
                f_point = Point(coordinates=(float(x), float(y)), crs=crs.Named(properties={"name": 'urn:ogc:def:crs:OGC:1.3:CRS84'}))
                f_obj = Feature(geometry=f_point, properties={'name': name, 'description': description, 'procedure': procedure}, id=i)
                featuresAr.append(f_obj)
                i = i + 1

            # create and return FeatureCollection from geojson package
            fcoll = FeatureCollection(featuresAr)

            with open(settings.MEDIA_ROOT + 'cache/sos_stations_' + str(self.id) + '.json', 'w') as f:
                dump(fcoll, f)

            return fcoll

    def download(self, request):
        if self.download_perm is True:
            if not request.user.is_authenticated():
                raise HttpResponse('Layer download is protected. You are not authenticated. Please log in.')
            elif request.user not in self.download_users.all() and len(
                    set(list(request.user.groups.all())) & set(list(self.download_groups.all()))) == 0 and request.user.is_superuser is not True:
                raise HttpResponse('Layer download is protected. You are not allowed to download this layer.')

        link = None
        if self.download_file != '':
            link = self.download_file.url
        elif self.download_url != '':
            link = self.download_url
            if self.download_type == 'wcs':
                bbox = request.query_params.get('bbox')
                format = request.query_params.get('outputformat')
                if format is None:
                    format = 'GeoTIFF'

                bbox = bbox.split(',')
                bbox = [float(i) for i in bbox]

                from owslib.wcs import WebCoverageService
                wcs = WebCoverageService(self.download_url, version='1.0.0')
                l1 = wcs.contents[self.download_layer]
                resx = float(l1.grid.offsetvectors[0][0])
                resy = float(l1.grid.offsetvectors[1][1]) * -1.0
                min_x = l1.boundingBoxWGS84[0]
                min_y = l1.boundingBoxWGS84[1]

                range_min_x = bbox[0] - min_x
                range_min_y = bbox[1] - min_y
                range_max_x = bbox[2] - min_x
                range_max_y = bbox[3] - min_y

                range_min_x_pixels = int(range_min_x / resx)
                range_min_y_pixels = int(range_min_y / resy)
                range_max_x_pixels = int(range_max_x / resx)
                range_max_y_pixels = int(range_max_y / resy)

                bbox_min_x = min_x + (range_min_x_pixels * resx)
                bbox_min_y = min_y + (range_min_y_pixels * resy)
                bbox_max_x = min_x + (range_max_x_pixels * resx)
                bbox_max_y = min_y + (range_max_y_pixels * resy)

                bbox = ','.join([str(bbox_min_x), str(bbox_min_y), str(bbox_max_x), str(bbox_max_y)])

                import requests
                url = self.download_url + '?service=WCS&request=GetCoverage&version=1.0.0&COVERAGE=' + self.download_layer + '&BBOX=' + \
                      bbox + '&CRS=EPSG:4326&format=' + format + '&RESPONSE_CRS=EPSG:4326&RESX=' + str(resx) + '&RESY=' + str(resy)  # noqa E127
                return url

                # old code
                data = requests.get(url)
                content_type = data.headers['CONTENT-TYPE']

                response = HttpResponse(str(data.content), content_type=content_type)
                filename = 'download.bin'
                if 'tiff' in content_type.lower():
                    filename = 'download.tif'
                elif 'hdf' in content_type.lower():
                    filename = 'download.hdf'
                elif 'nitf' in content_type.lower() or 'ntf' in content_type.lower():
                    filename = 'download.nitf'
                elif 'xml' in content_type.lower():
                    filename = 'download.xml'
                response['Content-Disposition'] = 'attachment; filename=%s' % (filename)
                return response
        else:
            raise Http404

        return link

    class Meta:
        ordering = ['title']


from django.db.models.signals import post_save  # noqa E402
from django.dispatch import receiver  # noqa E402


@receiver(post_save, sender=Layer)
def post_save_layer_sos(sender, instance, **kwargs):
    if instance.ogc_type == 'SOS':
        instance.cache()


# Layergroup model to group layers, just title is needed, the layers were referenced in the LayerInline model
class Layergroup(models.Model):
    title = models.CharField(max_length=200)

    def __str__(self):
        return u"%s" % (self.title)


# Sortable LayerInline model to reference layers and layergroups
# Foreign keys: Layer, Layergroup
# We can specify an own title for the layer in this group, if no one is specified, the original title from the layer is used
class LayerInline(models.Model):
    title = models.CharField(max_length=200, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE)
    layergroup = models.ForeignKey(Layergroup, on_delete=models.PROTECT)

    def __str__(self):
        if self.title is not None:
            return self.title
        else:
            return self.layer.title


# Sortable LayergroupInline model to reference mapviewers and layergroups
# Foreign Keys: Layergroup, MapViewer
class LayergroupInline(models.Model):
    order = models.PositiveIntegerField(default=0)
    layergroup = models.ForeignKey(Layergroup, on_delete=models.CASCADE)
    mapviewer = models.ForeignKey('mapviewer.MapViewer', on_delete=models.PROTECT)

    def __str__(self):
        return self.layergroup.title


class OnlineResourceInline(models.Model):
    order = models.PositiveIntegerField(default=0)
    linkage = models.CharField(max_length=400, blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    protocol = models.CharField(max_length=200, blank=True, null=True)
    description = models.CharField(max_length=500, blank=True, null=True)
    function = models.ForeignKey(ISOcodelist, limit_choices_to={'code_list': 'CI_OnLineFunctionCode'}, on_delete=models.PROTECT, blank=True, null=True)
    layer = models.ForeignKey(Layer, related_name='layer_online_resource', on_delete=models.CASCADE)

    def __str__(self):
        return self.linkage


class OnlineResourceInlineSerializer(serializers.ModelSerializer):
    function = ISOcodelistSerializer(read_only=True)

    class Meta:
        model = OnlineResourceInline
        fields = ('linkage', 'name', 'protocol', 'description', 'function')


class ConstraintLimitInline(models.Model):
    order = models.PositiveIntegerField(default=0)
    constraints_limit = models.CharField("Limitations on public access", max_length=400, blank=True, null=True)
    layer = models.ForeignKey(Layer, related_name='layer_constraints_limit', on_delete=models.CASCADE)

    def __str__(self):
        return self.constraints_limit


class ConstraintLimitInlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConstraintLimitInline
        fields = ('constraints_limit',)


class ConstraintConditionsInline(models.Model):
    order = models.PositiveIntegerField(default=0)
    constraints_cond = models.CharField("Conditions applying to access and use", max_length=400, blank=True, null=True)
    layer = models.ForeignKey(Layer, related_name='layer_constraints_cond', on_delete=models.CASCADE)

    def __str__(self):
        return self.constraints_cond


class ConstraintConditionsInlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConstraintConditionsInline
        fields = ('constraints_cond',)


class ConformityInline(models.Model):
    order = models.PositiveIntegerField(default=0)
    title = models.CharField("Conformity", max_length=400, blank=True, null=True)
    date = models.DateField(blank=True, null=True, verbose_name="Date")
    date_type = models.ForeignKey(ISOcodelist, limit_choices_to={'code_list': "CI_DateTypeCode"}, on_delete=models.PROTECT, blank=True,
                                  verbose_name="Date type")
    layer = models.ForeignKey(Layer, related_name='layer_conformity', on_delete=models.CASCADE)

    def __str__(self):
        return self.title


class ConformityInlineSerializer(serializers.ModelSerializer):
    date_type = ISOcodelistSerializer(read_only=True)

    class Meta:
        model = ConformityInline
        fields = ('title', 'date', 'date_type')


class KeywordInline(models.Model):
    order = models.PositiveIntegerField(default=0)
    keyword = models.CharField(max_length=200)
    uri = models.CharField(max_length=400, verbose_name="URI", blank=True, null=True)
    thesaurus_name = models.CharField(max_length=300, blank=True, null=True)
    thesaurus_date = models.DateField(blank=True, null=True, verbose_name="Thesaurus publication date")
    thesaurus_date_type_code_code_value = models.ForeignKey(ISOcodelist, limit_choices_to={'code_list': "CI_DateTypeCode"}, on_delete=models.PROTECT,
                                                            blank=True, null=True)
    layer = models.ForeignKey(Layer, related_name='layer_keywords', on_delete=models.CASCADE)

    def __str__(self):
        return self.keyword


class KeywordInlineSerializer(serializers.ModelSerializer):
    thesaurus_date_type_code_code_value = ISOcodelistSerializer(read_only=True)

    class Meta:
        model = KeywordInline
        fields = ('keyword', 'thesaurus_name', 'thesaurus_date', 'thesaurus_date_type_code_code_value', 'uri')


# Layer serializer used when add layer to map to retrieve fields needed for frontend (e.g., legend, downloadable)
# Also used in MapViewerDetail view
class LayerSerializer(serializers.ModelSerializer):
    # legend = serializers.FileField(source='legend_graphic') or serializers.CharField(source='legend_url')
    download = serializers.FileField(source='download_file') or serializers.CharField(source='download_url')

    class Meta:
        model = Layer
        fields = (
            'id', 'identifier', 'title', 'alternate_title', 'abstract', 'ogc_link', 'ogc_layer', 'ogc_type',
            'ogc_time', 'ogc_times', 'ogc_imageformat', 'ogc_attribution', 'west', 'east', 'north', 'south', 'dataset_epsg',
            'downloadable', 'legend_url', 'legend_graphic', 'legend_colors', 'legend_info', 'download', 'download_type', 'map_layout_image',
            'wmts_matrixset', 'wmts_resolutions', 'wmts_tilesize', 'wmts_projection', 'wmts_multiply', 'wmts_prefix_matrix_ids',
            'min_zoom', 'max_zoom', 'meta_file_info', 'resolution_distance', 'resolution_unit', 'statistic')


# Metadata serializer to output metadata related information from a given layer
class MetadataSerializer(serializers.ModelSerializer):
    point_of_contacts = ContactSerializer(many=True, read_only=True)
    meta_contacts = ContactSerializer(many=True, read_only=True)
    topicCategory = ISOcodelistSerializer(many=True, read_only=True)
    spat_representation_type = ISOcodelistSerializer(read_only=True)
    scope = ISOcodelistSerializer(read_only=True)
    layer_keywords = KeywordInlineSerializer(many=True, read_only=True)
    layer_constraints_cond = ConstraintConditionsInlineSerializer(many=True, read_only=True)
    layer_constraints_limit = ConstraintLimitInlineSerializer(many=True, read_only=True)
    layer_conformity = ConformityInlineSerializer(many=True, read_only=True)
    layer_online_resource = OnlineResourceInlineSerializer(many=True, read_only=True)

    class Meta:
        model = Layer
        fields = (
            'title', 'identifier', 'abstract', 'topicCategory', 'scope', 'layer_keywords', 'layer_constraints_cond', 'layer_constraints_limit',
            'layer_conformity',
            'layer_online_resource', 'ogc_link', 'ogc_layer', 'ogc_type', 'point_of_contacts', 'meta_contacts', 'date_creation', 'date_publication',
            'date_revision', 'language', 'characterset', 'format', 'west', 'east', 'north', 'south', 'geo_description', 'spat_representation_type',
            'equi_scale',
            'resolution_distance', 'resolution_unit', 'meta_contact', 'meta_language', 'meta_characterset', 'meta_date', 'meta_lineage', 'date_begin',
            'date_end',
            'dataset_epsg')
