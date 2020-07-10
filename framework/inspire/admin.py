from django.contrib.gis import admin
from suit.sortables import SortableModelAdmin

from layers.admin import LayersAdmin
from .models import InpireLayer
from content.admin import make_downloadable, make_non_downloadable, make_publishable, make_unpublishable

class InspireLayerAdmin(LayersAdmin):
    fieldsets = LayersAdmin.fieldsets + ((None, {
        'classes': ('suit-tab', 'suit-tab-swos',),
        'fields': ('internal_contact', 'responsible_city_department')
    }),)
    list_display=('title','publishable', 'downloadable', 'internal_contact')
    suit_form_tabs = LayersAdmin.suit_form_tabs + (('swos','SWOS'),)
    search_fields=('title','abstract','inspire_theme__name')
    ordering =['title']
    list_filter=('publishable', 'downloadable')
    suit_list_filter_horizontal = ('publishable', 'downloadable')

    actions=[make_publishable,make_unpublishable, make_downloadable, make_non_downloadable]

admin.site.register(InpireLayer, InspireLayerAdmin)