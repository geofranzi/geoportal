from django.contrib.gis import admin
from suit.sortables import SortableModelAdmin

from suit.sortables import SortableTabularInline

from layers.admin import LayersAdmin
from .models import InpireLayer, ProcessingInline, InspireMap
from content.admin import make_downloadable, make_non_downloadable, make_publishable, make_unpublishable

class ProcessingInlineTab(SortableTabularInline):
    model = ProcessingInline
    extra = 1
    verbose_name_plural = "Processing"
    suit_classes = 'suit-tab suit-tab-processing'

class InspireLayerAdmin(LayersAdmin):
    fieldsets = LayersAdmin.fieldsets + (
    (None, {
        'classes': ('suit-tab', 'suit-tab-internal',),
        'fields': ('internal_contact', 'internal_responsible_city_department', 'internal_legal_basis', 'internal_access_constraint')
    }),
    (None, {
        'classes': ('suit-tab', 'suit-tab-inspire',),
        'fields': ('inspireidentified', 'inspire_title', 'inspire_abstract', 'inspire_epsg', 'inspire_theme', 'processing_new_dataset')
    }),
    )
    inlines = LayersAdmin.inlines + (ProcessingInlineTab, )
    list_display=('title','publishable', 'downloadable', 'internal_contact')
    suit_form_tabs = LayersAdmin.suit_form_tabs + (('internal','Internal'),('inspire','INSPIRE'),('processing', 'Processing'))
    search_fields=('title','abstract','inspire_theme__name')
    ordering =['title']
    list_filter=('publishable', 'downloadable')
    suit_list_filter_horizontal = ('publishable', 'downloadable')

    actions=[make_publishable,make_unpublishable, make_downloadable, make_non_downloadable]

class InspireMapAdmin(admin.ModelAdmin):
    fieldsets =  (
        (None, {
            'classes': ('suit-tab', 'suit-tab-contact',),
            'fields': ('coordination_contact', 'data_contact', 'service_contact', 'metadata_contact')
        }),
        (None, {
            'classes': ('suit-tab', 'suit-tab-wms',),
            'fields': ('ows_contact', 'ows_title_de', 'ows_title_en', 'ows_abstract_de', 'ows_abstract_en', 'ows_rootlayer_title_de')
        }),
    )
   # inlines = (ProcessingInline, )
    list_display=('ows_title_de','ows_title_en')
    suit_form_tabs = (('contact','contact'),('wms','OWS/WMS/WFS'))
  #  search_fields=('title','abstract','inspire_theme__name')
  #  ordering =['title']
 #  list_filter=('publishable', 'downloadable')
  #  suit_list_filter_horizontal = ('publishable', 'downloadable')

admin.site.register(InpireLayer, InspireLayerAdmin)
admin.site.register(InspireMap, InspireMapAdmin)