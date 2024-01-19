from django.contrib.gis import admin

from .models import (CfStandardNames, ClimateChangeScenario, ClimateLayer, ClimateModelling, ClimateModellingBase,
                     ClimatePeriods, ProcessingMethod, ClimateVariable, CoupledModelIntercomparisonProject, GlobalClimateModel,
                     RegionalClimateModel,)


class CfStandardNamesAdmin(admin.ModelAdmin):
    list_display = ('entry_id', 'canonical_units', 'description')


class ClimateLayerAdmin(admin.ModelAdmin):
    list_display = ('title', 'dataset', 'get_variable_abbr', 'frequency', 'processing_method', 'cf_version')
    list_filter = ('variable', 'frequency', 'processing_method', 'cf_version')
    search_fields = ('variable__name', 'frequency__name', 'processing_method__name', 'cf_version__name')

    def get_variable_abbr(self, obj):
        return obj.variable.variable_abbr


class ClimateVariableAdmin(admin.ModelAdmin):
    list_display = ('variable_abbr', 'variable_name')
    search_fields = ('variable_abbr', 'variable_name')


class ClimateModellingAdmin(admin.ModelAdmin):
    list_display = ('modellingBase', 'scenario', 'ref_and_proj_periods', 'bias_correction_method')


class ClimateModellingBaseAdmin(admin.ModelAdmin):
    list_display = ('forcing_global_model', 'regional_model', 'project', 'experiment_id')


class ClimatePeriodsAdmin(admin.ModelAdmin):
    list_display = ('start_date', 'end_date')


class ClimateChangeScenarioAdmin(admin.ModelAdmin):
    list_display = ('name_short',)


class CoupledModelIntercomparisonProjectAdmin(admin.ModelAdmin):
    list_display = ('name_short',)


class GlobalClimateModelAdmin(admin.ModelAdmin):
    list_display = ('name_short',)


class RegionalClimateModelAdmin(admin.ModelAdmin):
    list_display = ('name_short',)

class ProcessingMethodAdmin(admin.ModelAdmin):
    list_display = ('name',)

admin.site.register(CfStandardNames, CfStandardNamesAdmin)
admin.site.register(ClimateLayer, ClimateLayerAdmin)
admin.site.register(ClimateVariable, ClimateVariableAdmin)
admin.site.register(ClimateModellingBase, ClimateModellingBaseAdmin)
admin.site.register(ClimateModelling, ClimateModellingAdmin)
admin.site.register(ClimatePeriods, ClimatePeriodsAdmin)
admin.site.register(ClimateChangeScenario, ClimateChangeScenarioAdmin)
admin.site.register(CoupledModelIntercomparisonProject, CoupledModelIntercomparisonProjectAdmin)
admin.site.register(GlobalClimateModel, GlobalClimateModelAdmin)
admin.site.register(RegionalClimateModel, RegionalClimateModelAdmin)
admin.site.register(ProcessingMethod, ProcessingMethodAdmin)
admin.site.site_header = 'Climate Administration'
