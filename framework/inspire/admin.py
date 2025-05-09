from django.contrib import messages
from django.contrib.gis import admin
from django.utils.translation import ngettext
from suit.sortables import SortableTabularInline

from inspire.csw import (create_csw_view_xml, create_csw_xml, create_update_csw,)
from layers.admin import LayersAdmin
from map.admin import MapAdmin

from .models import (InspireDataset, InspireHVD, InspireMap, InspireTheme, ProcessingInline, SourceLayer,)


def create_csw(self, request, queryset):
    count = len(queryset)
    for item in queryset:
        result = create_csw_xml(item, "inspire")
        if result["error"]:
            self.message_user(request, result["error_msg"], messages.ERROR)
            count = count - 1

    self.message_user(request, ngettext(
        '%d file was successfully created',
        '%d files were successfully created.',
        count,
    ) % count, messages.SUCCESS)


create_csw.short_description = "Create INSPIRE Dataset XML"


def create_csw_source(self, request, queryset):
    count = len(queryset)
    for item in queryset:
        result = create_csw_xml(item, "source")
        if result["error"]:
            self.message_user(request, result["error_msg"], messages.ERROR)
            count = count - 1
        item.inspire_published = True
        item.save()

    self.message_user(request, ngettext(
        '%d file was successfully created',
        '%d files were successfully created.',
        count,
    ) % count, messages.SUCCESS)


create_csw_source.short_description = "Create Source Dataset XML"


def update_csw(self, request, queryset):
    for item in queryset:
        create_update_csw(item, True)


update_csw.short_description = "Create and Update CSW"


def create_view_csw(modeladmin, request, queryset):
    for item in queryset:
        create_csw_view_xml(item, True)


create_view_csw.short_description = "Create View/Service XML"


class ProcessingInlineTab(SortableTabularInline):
    model = ProcessingInline
    extra = 1
    verbose_name_plural = "Processing"
    suit_classes = 'suit-tab suit-tab-processing'


class SourceLayerAdmin(LayersAdmin):
    fieldsets = LayersAdmin.fieldsets + (
        (None, {
            'classes': ('suit-tab', 'suit-tab-internal',),
            'fields': ('internal_contact', 'internal_responsible_city_department', 'internal_legal_basis',
                       'internal_access_constraint', 'internal_comment')
        }),
        (None, {
            'classes': ('suit-tab', 'suit-tab-inspire',),
            'fields': ('inspireidentified', 'opendata', 'inspire_theme')
        }),
    )
    inlines = LayersAdmin.inlines
    list_display = ('title', 'check_csw_published', 'internal_contact')
    suit_form_tabs = LayersAdmin.suit_form_tabs + (
        ('internal', 'Internal'), ('inspire', 'INSPIRE'))
    search_fields = ('title', 'abstract', 'inspire_theme__name')
    ordering = ['title']
    list_filter = ('publishable', 'downloadable')
    suit_list_filter_horizontal = ('publishable', 'downloadable')

    actions = [create_csw_source]  # make_publishable, make_unpublishable, make_downloadable, make_non_downloadable,


class InspireLayerAdmin(LayersAdmin):
    fieldsets = LayersAdmin.fieldsets + (

        (None, {
            'classes': ('suit-tab', 'suit-tab-inspire',),
            'fields': ('inspireidentified', 'opendata', 'inspire_theme', 'inspire_hvd',),
        }),
    )
    inlines = LayersAdmin.inlines + (ProcessingInlineTab,)
    list_display = ('title', 'check_csw_published', 'inspire_hvd')
    suit_form_tabs = LayersAdmin.suit_form_tabs + (
        ('inspire', 'INSPIRE'),)
    search_fields = ('title', 'abstract', 'inspire_theme__name')
    ordering = ['title']
    list_filter = ('publishable', 'downloadable')
    suit_list_filter_horizontal = ('publishable', 'downloadable')

    actions = [update_csw, create_csw]  # make_publishable, make_unpublishable, make_downloadable, make_non_downloadable,


class InspireMapAdmin(MapAdmin):
    fieldsets = MapAdmin.fieldsets + (
        (None, {
            'classes': ('suit-tab', 'suit-tab-inspire'),
            'fields': ('inspire_theme', 'inspire_hvd')
        }),

    )
    inlines = MapAdmin.inlines
    #  list_display=('title','publishable', 'downloadable', 'internal_contact')
    list_display = ('full_name', 'ows_title_de', 'ows_title_en', 'ows_url_name', 'inspire_hvd')
    suit_form_tabs = MapAdmin.suit_form_tabs + (('inspire', 'Inspire theme'),)
    search_fields = ('abstract', 'inspire_theme__name')

    actions = [create_view_csw]


# ordering =['title']
# list_filter=('publishable', 'downloadable')
# suit_list_filter_horizontal = ('publishable', 'downloadable')

# actions=[make_publishable,make_unpublishable, make_downloadable, make_non_downloadable, update_csw, create_csw]

class InspireThemeAdmin(admin.ModelAdmin):
    list_display = ('uri', 'name_en', 'name_de', 'definition_en', 'definition_de', "topicCategory")

    def has_add_permission(self, request):
        return False


class InspireHVDAdmin(admin.ModelAdmin):
    list_display = ('uri', 'name_en', 'name_de')

    def has_add_permission(self, request):
        return False


admin.site.register(InspireMap, InspireMapAdmin)
admin.site.register(SourceLayer, SourceLayerAdmin)
admin.site.register(InspireDataset, InspireLayerAdmin)
admin.site.register(InspireTheme, InspireThemeAdmin)
admin.site.register(InspireHVD, InspireHVDAdmin)
