from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from . import views


urlpatterns = [
    path('get_climate_layers', views.get_climate_layers, name='get_climate_layers'),
    path('get_climate_layer', views.get_climate_layer, name='get_climate_layer'),
    path('download', views.download, name='download'),
    path('search', views.Elasticsearch.as_view(), name="search"),
    path('search_collection', views.ElasticsearchCollections.as_view(), name="search_collection"),
]

urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json'])
