# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2020-05-21 09:30
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mapviewer', '0002_auto_20180712_1319'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mapviewer',
            name='template_file',
            field=models.FilePathField(match='.*\\.html', path='C:\\Users\\c1zafr\\PycharmProjects\\GEOPORTAL_INSPIRE\\geoportal\\framework\\templates/mapviewer', verbose_name='Template file'),
        ),
    ]