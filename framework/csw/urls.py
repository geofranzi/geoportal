#from django.conf.urls import url
from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^search/(?P<pk>[0-9]+)$', views.CSWRequest.as_view(), name='search'),
]