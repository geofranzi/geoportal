from django.db import models

from layers.models import Layer


# Create your models here.
class ValidationLayer(Layer):
    layer_basemap = models.ForeignKey(Layer, related_name="validation_layer_basemap", on_delete=models.PROTECT, verbose_name="Background layer")
    layer_auxiliary =  models.ManyToManyField(Layer, related_name="validation_layer_auxiliary", verbose_name="Validation auxiliary layers", blank=True)
    legend = models.CharField("Classification legend", max_length=200, choices=[('MAES', 'MAES'), ('CLC', 'CLC'), ('LCCS', 'LCCS')], blank=True, null=True)
