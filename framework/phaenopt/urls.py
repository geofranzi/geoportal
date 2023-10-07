# from django.conf.urls import url
from django.urls import re_path

from . import (models, views,)


# register URLs for each app + media URLs
urlpatterns = [
    re_path(r'^region/(?P<pk>[0-9]+)$', views.RegionDetail.as_view(), name='region_detail'),
    re_path(r'^region/(?P<region_id>[0-9]+)/citizenscience/data.json$', views.RegionCitizenScienceDataInitial.as_view(), name='region_csproject_data'),
    re_path(r'^region/(?P<region_id>[0-9]+)/csproject/(?P<project_id>[0-9]+)/data.json$', views.RegionCitizenScienceData.as_view(), name='region_csproject_data'),
    re_path(r'^region/(?P<region_id>[0-9]+)/dwd/stations.json$', views.DWDStations.as_view(), name='region_dwd_stations'),
    re_path(r'^region/(?P<region_id>[0-9]+)/dwd/stations.geojson$', views.DWDStationsGeometry.as_view(), name='region_dwd_stations'),
    re_path(r'^dwd/station/(?P<pk>[0-9]+).json$', views.DWDStationView.as_view(), name='region_dwd_stations'),
    re_path(r'^dwd/station/plot.png$', views.DWDInSituData_Phase.as_view(), name='region_dwd_stations'),
    re_path(r'^dwd/definitions.json$', views.DWDInSituDataPhases.as_view(), name='region_dwd_stations'),
    re_path(r'^dwd/definitions/plot.png', views.DWDInSituData_PhaseHistogram.as_view(), name='region_dwd_stations'),

]

