# Generated by Django 4.2.4 on 2023-11-12 18:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        
        ('climate', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClimateChangeScenario',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name_short', models.CharField(max_length=255, unique=True)),
                ('name_long', models.CharField(blank=True, max_length=500, null=True)),
                ('code', models.CharField(blank=True, max_length=255, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('web_url', models.TextField(blank=True, max_length=500, null=True)),
                ('type', models.CharField(blank=True, choices=[('RCP', 'RCP'), ('SSP', 'SSP'), ('Other', 'Other'), ('', 'None')], max_length=255, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='ClimateLayer',
            fields=[
                ('layer_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='layers.layer')),
                ('frequency', models.CharField(blank=True, choices=[('daily', 'daily'), ('monthly', 'monthly'), ('yearly', 'yearly')], max_length=20, null=True)),
                ('cf_version', models.CharField(blank=True, max_length=20, null=True)),
                ('local_path', models.TextField(blank=True, null=True)),
                ('file_name', models.CharField(blank=True, max_length=500, null=True)),
                ('size', models.FloatField(blank=True, null=True, verbose_name='Size (GB)')),
                ('status', models.CharField(blank=True, choices=[('planned', 'planned'), ('internal', 'internal'), ('public', 'public')], max_length=20, null=True)),
            ],
            bases=('layers.layer',),
        ),
        migrations.CreateModel(
            name='ClimateModelling',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='ClimateModellingBase',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('experiment_id', models.CharField(blank=True, max_length=255, null=True)),
                ('forcing_global_model', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='climate.globalclimatemodel', verbose_name='Global Climate Model')),
                ('project', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='climate.coupledmodelintercomparisonproject', verbose_name='Coupled Model Intercomparison Project')),
                ('regional_model', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='climate.regionalclimatemodel', verbose_name='Regional Climate Model')),
            ],
        ),
        migrations.CreateModel(
            name='ClimatePeriods',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='ClimateProjections',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('proj_period', models.ManyToManyField(blank=True, related_name='proj_period_period', to='climate.climateperiods', verbose_name='Projection Period(s)')),
                ('ref_period', models.ManyToManyField(blank=True, related_name='ref_period_period', to='climate.climateperiods', verbose_name='Reference Period(s)')),
            ],
        ),
        migrations.CreateModel(
            name='ClimateVariable',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('variable_abbr', models.CharField(blank=True, max_length=20, null=True)),
                ('variable_name', models.CharField(blank=True, max_length=255, null=True)),
                ('variable_unit', models.CharField(blank=True, max_length=255, null=True)),
                ('variable_cell_methods', models.CharField(blank=True, max_length=255, null=True)),
                ('variable_description', models.TextField(blank=True, null=True)),
                ('variable_type', models.CharField(blank=True, choices=[('raw', ''), ('indicator', 'indicator')], default='raw', max_length=20, null=True)),
                ('variable_ref_url', models.TextField(blank=True, max_length=500, null=True)),
                ('variable_standard_name_cf', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='Variable', to='climate.cfstandardnames')),
            ],
        ),
        migrations.CreateModel(
            name='ProcessingMethod',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('type', models.CharField(blank=True, choices=[('Bias Correction', 'Bias Correction'), ('Downscaling', 'Downscaling'), ('Other', 'Other'), ('', 'None')], null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('ref_url', models.TextField(blank=True, max_length=500, null=True)),
                ('ref_citation', models.TextField(blank=True, max_length=500, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='ProvenanceInline',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('relation_type', models.CharField(blank=True, choices=[('isPartOf', 'isPartOf'), ('isVersionOf', 'isVersionOf'), ('isBasedOn', 'isBasedOn'), ('isComposedOf', 'isComposedOf'), ('isDescribedBy', 'isDescribedBy'), ('isDerivedFrom', 'isDerivedFrom'), ('isFormatOf', 'isFormatOf'), ('isIdenticalTo', 'isIdenticalTo'), ('isMetadataFor', 'isMetadataFor'), ('isNextVersionOf', 'isNextVersionOf'), ('isPreviousVersionOf', 'isPreviousVersionOf'), ('isSourceOf', 'isSourceOf'), ('isSupplementTo', 'isSupplementTo'), ('isSupplementedBy', 'isSupplementedBy'), ('isVariantFormOf', 'isVariantFormOf'), ('references', 'references'), ('replaces', 'replaces'), ('requires', 'requires'), ('source', 'source')], max_length=20, null=True)),
                ('climate_layer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='Climate_Layer', to='climate.climatelayer')),
                ('target', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='Target', to='climate.climatelayer')),
            ],
        ),
        migrations.DeleteModel(
            name='Scenario',
        ),
        migrations.AddField(
            model_name='climatemodel',
            name='type',
            field=models.CharField(blank=True, choices=[('Global', 'Global'), ('Regional', 'Regional'), ('Local', 'Local'), ('Other', 'Other'), ('', 'None')], default='None', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='climatemodel',
            name='publisher',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='Publisher', to='layers.contact'),
        ),
        migrations.AddField(
            model_name='climatemodelling',
            name='bias_correction_method',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='climate.processingmethod', verbose_name='Bias Correction Method'),
        ),
        migrations.AddField(
            model_name='climatemodelling',
            name='modellingBase',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='climate.climatemodellingbase', verbose_name='Modelling Base'),
        ),
        migrations.AddField(
            model_name='climatemodelling',
            name='ref_and_proj_periods',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='climate.climateperiods', verbose_name='Reference and Projection Period(s)'),
        ),
        migrations.AddField(
            model_name='climatemodelling',
            name='scenario',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='climate.climatechangescenario', verbose_name='Scenario'),
        ),
        migrations.AddField(
            model_name='climatelayer',
            name='dataset',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='climate.climatemodellingbase', verbose_name='Climate Dataset'),
        ),
        migrations.AddField(
            model_name='climatelayer',
            name='processing_method',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='climate.processingmethod', verbose_name='Processing Method'),
        ),
        migrations.AddField(
            model_name='climatelayer',
            name='variable',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='climate.climatevariable', verbose_name='Climate Variable'),
        ),
    ]