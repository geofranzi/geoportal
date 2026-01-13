from rest_framework import serializers
from .models import FolderType
from .models import ClimateLayer


class ClimateLayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClimateLayer
        fields = ('dataset', 'frequency', 'cf_version', 'processing_method', 'variable', 'local_path', 'file_name', 'size', 'status', 'download_path')


class FolderTypeSerializer(serializers.ModelSerializer):
    bbox = serializers.SerializerMethodField()

    class Meta:
        model = FolderType
        fields = [
            "key",
            "display_name",
            "description",
            "citation",
            "header_regex",
            "lineage",
            "status",
            "bbox",
        ]

    def get_bbox(self, obj):
        return [
            obj.bbox_min_lon,
            obj.bbox_min_lat,
            obj.bbox_max_lon,
            obj.bbox_max_lat,
        ]
