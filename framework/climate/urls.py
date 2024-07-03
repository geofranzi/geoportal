from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from . import views


urlpatterns = [
    path('test_xclim', views.test_xclim, name='test_xclim'),
    path('get_climate_layers', views.get_climate_layers, name='get_climate_layers'),
    path('get_climate_layer', views.get_climate_layer, name='get_climate_layer'),
    path('download', views.download, name='download'),
    path('search', views.Elasticsearch.as_view(), name="search"),
    path('search_collection', views.ElasticsearchCollections.as_view(), name="search_collection"),
    path('search_indicator', views.ElasticsearchIndicators.as_view(), name="search_indicator"),
    path('get_temp_urls', views.get_temp_urls, name='get_temp_urls'),
    path('select_temp_urls', views.select_temp_urls, name='select_temp_urls'),
    path('get_content', views.FolderContentView.as_view(), name='get_content'),
    path('get_temp_file', views.TempDownloadView.as_view(), name='get_temp_file'),
    path('get_temp_file_metadata', views.get_ncfile_metadata, name='get_ncfile_metadata'),
    path('access_tif', views.access_tif_from_ncfile, name="access_tif"),
]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json'])
