from django import forms
from django.contrib.gis import admin


from suit.sortables import SortableStackedInline, SortableTabularInline  # isort:skip
from .models import ConformityMapInline, ConstraintConditionsMapInline, ConstraintLimitMapInline, KeywordMapInline, Map, MapLayerInline  # isort:skip
from .models import MapLayerStyle, OnlineResourceMapInline   # isort:skip


class OnlineResourceMapInlineSort(SortableTabularInline):
    model = OnlineResourceMapInline
    extra = 1
    verbose_name_plural = 'Online Resources'
    suit_classes = 'suit-tab suit-tab-onlineresources'


class ConstraintLimitMapInlineSort(SortableTabularInline):
    model = ConstraintLimitMapInline
    extra = 1
    verbose_name_plural = "Constraint Limits"
    suit_classes = 'suit-tab suit-tab-conformity_constraints'


class ConstraintConditionsMapInlineSort(SortableTabularInline):
    model = ConstraintConditionsMapInline
    extra = 1
    verbose_name_plural = "Constraint Conditions"
    suit_classes = 'suit-tab suit-tab-conformity_constraints'


class ConformityMapInlineForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super(ConformityMapInlineForm, self).clean()

        if cleaned_data.get('date_type') is None:
            self.add_error('date_type', 'Please specify a date type')
        if cleaned_data.get('date') is None:
            self.add_error('date', 'Please specify a date')


class ConformityMapInlineSort(SortableTabularInline):
    form = ConformityMapInlineForm
    model = ConformityMapInline
    extra = 1
    verbose_name_plural = "Conformity"
    suit_classes = 'suit-tab suit-tab-conformity_constraints'


class KeywordMapInlineSort(SortableTabularInline):
    model = KeywordMapInline
    extra = 1
    verbose_name_plural = "Keywords"
    suit_classes = 'suit-tab suit-tab-keyword'


class MapLayerInlineSort(SortableStackedInline):
    model = MapLayerInline
    extra = 0
    verbose_name_plural = "Layer"
    suit_classes = 'suit-tab suit-tab-layer'


class MapAdmin(admin.ModelAdmin):
    inlines = (OnlineResourceMapInlineSort, ConstraintConditionsMapInlineSort, ConstraintLimitMapInlineSort, ConformityMapInlineSort,
               KeywordMapInlineSort, MapLayerInlineSort)
    fieldsets = (
        (None, {
            'classes': ('suit-tab', 'suit-tab-contact',),
            'fields': ('distributor_contact', 'metadata_contact', 'service_contact')
        }),
        (None, {
            'classes': ('suit-tab', 'suit-tab-service',),
            'fields': ('service_name', 'service_abstract', 'service_publication_date', 'service_identifier')
        }),
        (None, {
            'classes': ('suit-tab', 'suit-tab-download',),
            'fields': ('download_name', 'download_abstract', 'download_publication_date', 'download_type', 'download_secure', 'download_identifier')
        }),
        (None, {
            'classes': ('suit-tab', 'suit-tab-location',),
            'fields': ('east', 'west', 'north', 'south', 'geo_description')
        }),
        (None, {
            'classes': ('suit-tab', 'suit-tab-wms',),
            'fields': ('ows_url_name', 'ows_contact', 'ows_title_de', 'ows_title_en', 'ows_abstract_de', 'ows_abstract_en', 'ows_style_name',
                       'ows_rootlayer_title_de', 'ows_rootlayer_title_en', 'ows_rootlayer_abstract_de', 'ows_rootlayer_abstract_en',
                       'ows_srs', 'ows_languages', 'ows_enable_request')
        }),
    )
    # inlines = (ProcessingInline, )
    list_display = ('full_name', 'ows_title_de', 'ows_title_en', 'ows_url_name')
    suit_form_tabs = (('contact', 'Contact'), ('wms', 'OWS/WMS/WFS'), ('keyword', 'Keywords'), ('service', 'Service'),
                      ('download', 'Download'), ('location', 'Location'), ('layer', 'Layer'),
                      ('onlineresources', 'Online Resources'), ('conformity_constraints', 'Conformity / Constraints'))


class MapLayerStyleAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {
            'classes': ('suit-tab', 'suit-tab-style',),
            'fields': ('name', 'description', 'template_file')
        }),
    )
    list_display = ('name', 'description')
    suit_form_tabs = (('style', 'Style'),)


# class MapGroupAdmin(admin.ModelAdmin):
#     fieldsets = (
#         (None, {
#             'classes': ('suit-tab', 'suit-tab-group',),
#             'fields': ('ows_group_title_de', 'ows_group_title_en', 'ows_group_abstract_de', 'ows_group_abstract_en')
#         }),
#     )
#     list_display = ('ows_group_title_de', 'ows_group_title_en', 'ows_group_abstract_de', 'ows_group_abstract_en')
#     suit_form_tabs = (('group', 'Group'),)


list_display = ('name', 'description')
suit_form_tabs = (('style', 'Style'),)

admin.site.register(Map, MapAdmin)
admin.site.register(MapLayerStyle, MapLayerStyleAdmin)
# admin.site.register(MapGroup, MapGroupAdmin)
