# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-06-15 19:02
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0002_satdatalayer_thema'),
    ]

    operations = [
        migrations.AlterField(
            model_name='satdatalayer',
            name='thema',
            field=models.CharField(choices=[('Rohdaten', 'Rohdaten'), ('Produkt', 'Produkt')], max_length=30, verbose_name='Type'),
        ),
    ]
