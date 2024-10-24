# Generated by Django 4.0.2 on 2023-10-01 21:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('geospatial', '0001_initial'),
        ('content', '0003_auto_20200615_2102'),
    ]

    operations = [
        migrations.AlterField(
            model_name='externaldatabase',
            name='region',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='external_region', to='geospatial.region', verbose_name='Region'),
        ),
        migrations.AlterField(
            model_name='externallayer',
            name='datasource',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='layer_datasource', to='content.externaldatabase', verbose_name='External Database'),
        ),
        migrations.AlterField(
            model_name='image',
            name='region',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='image_region', to='geospatial.region', verbose_name='Region'),
        ),
        migrations.AlterField(
            model_name='satdatalayer',
            name='region',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='layer_satdata', to='geospatial.region', verbose_name='Region'),
        ),
        migrations.AlterField(
            model_name='storyline',
            name='region',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='geospatial.region'),
        ),
        migrations.AlterField(
            model_name='storylineinline',
            name='story_line_part',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='story_line_parts', to='content.storylinepart'),
        ),
        migrations.AlterField(
            model_name='storylinepart',
            name='region',
            field=models.ForeignKey(help_text='Plaese click - Save and continue editing - to update the layer lists below', on_delete=django.db.models.deletion.PROTECT, to='geospatial.region'),
        ),
        migrations.AlterField(
            model_name='video',
            name='region',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='video_region', to='geospatial.region', verbose_name='Region'),
        ),
    ]
