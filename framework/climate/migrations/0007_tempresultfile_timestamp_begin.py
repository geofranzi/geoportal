# Generated by Django 4.2.5 on 2024-07-20 16:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('climate', '0006_tempresultfile'),
    ]

    operations = [
        migrations.AddField(
            model_name='tempresultfile',
            name='timestamp_begin',
            field=models.CharField(max_length=500, null=True),
        ),
    ]
