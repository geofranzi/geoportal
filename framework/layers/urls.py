# from django.conf.urls import url
from django.urls import re_path, path
from rest_framework.urlpatterns import format_suffix_patterns

from . import views


urlpatterns = [
    re_path(r'^list/$', views.LayerList.as_view(), name='layer_list'),
    re_path(r'^detail/(?P<pk>[0-9]+)$', views.LayerDetail.as_view(), name='layer_detail'),
    re_path(r'^detail/(?P<pk>[0-9]+)/download$', views.LayerDownload.as_view(), name='layer_download'),
    re_path(r'^info$', views.LayerInfo.as_view(), name='layer_feature_info'),
    re_path(r'^data$', views.DataRequest.as_view(), name='external_proxy'),
    re_path(r'^capabilities/time$', views.GetTimeValues.as_view(), name='layer_time_values'),
    re_path(r'^capabilities/WMS$', views.GetWMSCapabilities.as_view(), name='layer_capabilities_wms'),
    re_path(r'^capabilities/WMTS$', views.GetWMTSCapabilities.as_view(), name='layer_capabilities_wmts'),
    re_path(r'^sos/(?P<pk>[0-9]+)/stations$', views.GetSOSStations.as_view(), name='sos_stations'),
    re_path(r'^sos/data$', views.GetSOSObservation.as_view(), name='sos_data'),
    path('get_contacts_website', views.get_contacts_website, name='get_contacts_website'),
]

# Used for detail/<pk>.json


urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json'])
