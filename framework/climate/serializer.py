from rest_framework import serializers

from .models import ClimateLayer


class ClimateLayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClimateLayer
        fields = ('dataset', 'frequency', 'cf_version', 'processing_method', 'variable', 'local_path', 'file_name', 'size', 'status', 'download_path')
