# Generated by Django 2.0.1 on 2018-03-24 22:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0013_event'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='event',
            name='pennant_district',
        ),
    ]
