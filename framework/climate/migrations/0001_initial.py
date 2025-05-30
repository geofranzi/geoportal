# Generated by Django 4.2.4 on 2023-10-11 11:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True
    
    dependencies = [
        ('layers', '0013_alter_layer_progress_alter_layer_scope_and_more'),
    ]
   
    operations = [
        migrations.CreateModel(
            name='CfStandardNames',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entry_id', models.CharField(max_length=255, unique=True)),
                ('canonical_units', models.CharField(blank=True, max_length=255, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('grib', models.CharField(blank=True, max_length=255, null=True)),
                ('amip', models.CharField(blank=True, max_length=255, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='ClimateModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name_short', models.CharField(max_length=255, unique=True)),
                ('name_long', models.CharField(blank=True, max_length=500, null=True)),
                ('code', models.CharField(blank=True, max_length=255, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('web_url', models.TextField(blank=True, null=True)),
                ('version', models.CharField(blank=True, max_length=10, null=True)),
                ('versionDate', models.DateField(blank=True, null=True)),
                ('publisher', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='layers.contact', verbose_name='Publisher')),
            ],
        ),
        migrations.CreateModel(
            name='CoupledModelIntercomparisonProject',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name_short', models.CharField(max_length=255, unique=True)),
                ('name_long', models.CharField(blank=True, max_length=500, null=True)),
                ('code', models.CharField(blank=True, max_length=255, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('web_url', models.TextField(blank=True, max_length=500, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Scenario',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name_short', models.CharField(max_length=255, unique=True)),
                ('name_long', models.CharField(blank=True, max_length=500, null=True)),
                ('code', models.CharField(blank=True, max_length=255, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('web_url', models.TextField(blank=True, max_length=500, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='GlobalClimateModel',
            fields=[
                ('climatemodel_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='climate.climatemodel')),
            ],
            bases=('climate.climatemodel',),
        ),
        migrations.CreateModel(
            name='RegionalClimateModel',
            fields=[
                ('climatemodel_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='climate.climatemodel')),
            ],
            bases=('climate.climatemodel',),
        ),
    ]
