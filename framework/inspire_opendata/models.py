from django.db import models
from django.contrib.auth.models import User, Group
from django.db.models import Q
from django.http import Http404, HttpResponse
from rest_framework import serializers
from django.contrib.gis.db import models


from layers.models import Layer, ISOcodelist, KeywordInline, Contact
from content.models import Country
from geospatial.models import Region

import json

class inpire_opendataLayer(Layer):
    internal_contact =models.ForeignKey(Contact, related_name="internal_contact", verbose_name="Internal Contact", blank=True, null=True)
    responsible_city_department = models.ForeignKey(Contact, related_name=" ", limit_choices_to= Q(organisation_startswith="Stadt Hameln - Fachabteilung"))
    type = models.TextField(max_length=20, choices=[('intern', 'intern'), ('OpenData', 'OpenData'), ('INSPIRE', 'INSPIRE')], default="intern")
    status = models.TextField(max_length=20, )
    #transformation



