# from django.conf.urls import url
# from djgeojson.views import GeoJSONLayerView

from django.urls import re_path

from . import (models, views,)


#class MapLayer(GeoJSONLayerView):
    # Options
    #precision = 4   # float


# register URLs for each app + media URLs
urlpatterns = [
    re_path(r'^wetlands.json$', views.WetlandsList.as_view(), name='wetland_list'),
    re_path(r'^wetlands.geojson$', views.WetlandGeometry.as_view(), name="wetland_geometry"), # replace dynamic create wetlands.geojson by static file
    re_path(r'^wetland/(?P<pk>[0-9]+)$', views.WetlandDetail.as_view(), name='wetland_detail'),
    re_path(r'^wetland/(?P<pk>[0-9]+)/panoramio.json$', views.Panoramio.as_view(), name='wetland_panoramio'),
    re_path(r'^wetland/(?P<pk>[0-9]+)/images.json$', views.WetlandImages.as_view(), name='wetland_images'),
    re_path(r'^wetland/(?P<pk>[0-9]+)/youtube.json$', views.YouTube.as_view(), name='wetland_youtube'),
    re_path(r'^wetland/(?P<pk>[0-9]+)/satdata.json$', views.SatelliteData.as_view(), name='wetland_satdata'),
    re_path(r'^wetland/(?P<pk>[0-9]+)/satdata/metadata$', views.SatelliteMetadata.as_view(), name='wetland_satmetadata'),
    re_path(r'^wetland/layer/(?P<pk>[0-9]+)/colors.json$', views.LayerColors.as_view(), name='wetland_layer_colors'),
    re_path(r'^(?P<pk>[0-9]+)/storyline.json$', views.StoryLineData.as_view(), name='wetland_story_line'),
    re_path(r'^searchresult.json$', views.Elasticsearch.as_view(), name="search"),
    re_path(r'^layer.json$', views.Layer.as_view(), name="layer"),
    re_path(r'^download$', views.DownloadData.as_view(), name="download_test"),
    re_path(r'^download_as_archive$', views.DownloadFiles.as_view(), name="download_archive"),
    re_path(r'^list_files$', views.ListFilesForDownload.as_view(), name="list_files"),
    re_path(r'^wetland/(?P<pk>[0-9]+)/satdata/download$', views.DownloadDataSentinel.as_view(), name="download_test2"),
    re_path(r'^wetland/(?P<pk>[0-9]+)/satdata/results', views.SatelliteMetadataExport.as_view(), name="download_satdata_results"),
    re_path(r'^externaldb.json', views.GetExternalDatabases.as_view(), name="global_data"),
    re_path(r'^countries.json', views.GetCountries.as_view(), name="national_data_countries"),
    re_path(r'^(?P<pk>[0-9]+)/nationaldata.json', views.GetNationalData.as_view(), name="national_data"),
    re_path(r'^nationaldata/statistics.json', views.NationalWetlandStatistics.as_view(), name="national_data_statistics"),
]

