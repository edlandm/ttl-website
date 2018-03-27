# Generated by Django 2.0.1 on 2018-01-24 21:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PennantStandings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('win', models.IntegerField(default=0)),
                ('defend', models.IntegerField(default=0)),
                ('place', models.IntegerField(default=0)),
                ('venue', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='website.Venue')),
            ],
        ),
    ]
