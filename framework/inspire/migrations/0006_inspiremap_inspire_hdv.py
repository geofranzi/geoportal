# Generated by Django 4.2.5 on 2024-08-25 21:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inspire', '0005_remove_sourcelayer_inspire_hdv_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='inspiremap',
            name='inspire_hvd',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='inspire_hvd_map', to='inspire.inspirehvd'),
        ),
    ]
