# django-suit config
from django.apps import AppConfig
# from django.apps import AppConfig
from django.contrib import admin as ad
from django.contrib.admin.apps import AdminConfig
from suit.apps import DjangoSuitConfig
from suit.menu import (ChildItem, ParentItem,)

from webgis import settings


class SuitConfig(DjangoSuitConfig):
    layout = 'horizontal'  # vertical / horizontal
    menu = (
        ParentItem('Authorization', children=[
            ChildItem(model='auth.user'),
            ChildItem('User groups', 'auth.group')
        ], icon='fa fa-users'),
        ParentItem('Map Viewer', children=[
            ChildItem('Map Viewer', model='mapviewer.mapviewer')
        ]),
        ParentItem('Search', children=[
            ChildItem('Search', model='csw.csw')
        ]),
        ParentItem('Contact', children=[
            ChildItem('Contacts', model='layers.contact')
        ]),
        ParentItem('Lists', children=[
            ChildItem('Countries', model='swos.country'),
            ChildItem('ISO Code lists', model='layers.isocodelist'),
        ]),
        ParentItem('Layer', children=[
            ChildItem('Layer', model='layers.layer'),
            ChildItem('Layer Groups', model='layers.layergroup')
        ]),
        ParentItem('Geospatial', children=[
            ChildItem('Region', model='geospatial.region'),
        ]),
        ParentItem('Content', children=[
            ChildItem('Images', model='content.image'),
            ChildItem('Videos', model='content.video'),
            ChildItem('External Layers', model='content.externallayer'),
            ChildItem('External Databases', model='content.externaldatabase'),
            ChildItem('Story Lines', model='content.storyline'),
            ChildItem('Story Line Parts', model='content.storylinepart'),
            ChildItem('Story Line Features', model='content.storylinefeature'),
            ChildItem('Satdata Layers', model='content.satdatalayer'),
        ]),
        ParentItem('SWOS', children=[
            ChildItem('Wetlands', model='swos.wetland'),
            ChildItem('Wetland Layers', model='swos.wetlandlayer'),
            ChildItem('Wetland Products', model='swos.product'),
            ChildItem('Wetland Indicator', model='swos.indicator'),
        ]),
        ParentItem('PhaenOPT', children=[
            ChildItem('Layers', model='phaenopt.phenolayer'),
            ChildItem('Products', model='phaenopt.product'),
            ChildItem('Phenophases', model='phaenopt.pheno'),
            ChildItem('Citizen Science', model='phaenopt.citizenscienceproject'),
        ]),
        ParentItem('INSPIRE', children=[
            ChildItem('Source datasets', model='inspire.sourcelayer'),
            ChildItem('INSPIRE datasets', model='inspire.inspiredataset'),
            ChildItem('Maps', model='inspire.inspiremap'),
            ChildItem('Themes', model='inspire.inspiretheme'),
        ])
    )
    if "validation" in settings.INSTALLED_APPS:
        menu = menu + (
            (ParentItem('Validation', children=[ChildItem('Validation Layers', model='validation.validationlayer')])),)


class MyAdminSite(ad.AdminSite):
    enable_nav_sidebar = False


class MyAdminConfig(AdminConfig):
    default_site = 'webgis.apps.MyAdminSite'


class WebgisConfig(AppConfig):
    name = 'webgis'
