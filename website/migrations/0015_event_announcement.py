# Generated by Django 2.0.1 on 2018-03-25 20:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0014_remove_event_pennant_district'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='announcement',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='website.Announcement'),
        ),
    ]
