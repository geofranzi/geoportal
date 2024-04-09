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
    path('get_climate_txt', views.TextFileView.as_view(), name='get_climate_txt'),
    path('select_for_wget', views.SelectionForWgetView.as_view(), name='select_for_wget'),
    path('get_content', views.ContentView.as_view(), name='get_content'),
    path('get_file', views.GetFileView.as_view(), name='get_file'),
]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json'])
