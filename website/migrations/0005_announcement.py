# Generated by Django 2.0.1 on 2018-02-21 20:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0004_auto_20180220_0046'),
    ]

    operations = [
        migrations.CreateModel(
            name='Announcement',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('description', models.TextField(max_length=250)),
                ('url', models.CharField(blank=True, max_length=250, null=True)),
                ('image_url', models.CharField(blank=True, max_length=250, null=True)),
                ('display_start', models.DateTimeField(auto_now_add=True)),
                ('display_end', models.DateTimeField(blank=True, null=True)),
            ],
        ),
    ]
