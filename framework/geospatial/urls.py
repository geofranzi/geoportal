# from django.conf.urls import url

from django.urls import re_path

from . import views


# register URLs for each app + media URLs
urlpatterns = [
    re_path(r'^regions.json$', views.RegionsList.as_view(), name='region_list'),
    re_path(r'^regions.geojson$', views.RegionsGeometry.as_view(), name="region_geometry"),  # replace dynamic create wetlands.geojson by static file
    re_path(r'^region/(?P<pk>[0-9]+)$', views.RegionDetail.as_view(), name='region_detail'),
    re_path(r'^region/(?P<pk>[0-9]+)/satdata.json$', views.SatelliteData.as_view(), name='region_detail'),
    re_path(r'^region/(?P<pk>[0-9]+)/satdata/metadata$', views.SatelliteMetadata.as_view(), name='wetland_satmetadata'),
    re_path(r'^region/(?P<pk>[0-9]+)/satdata/results', views.SatelliteMetadataExport.as_view(), name="download_satdata_results"),
]
