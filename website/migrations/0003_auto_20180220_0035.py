# Generated by Django 2.0.1 on 2018-02-20 08:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0002_pennantstandings'),
    ]

    operations = [
        migrations.AlterField(
            model_name='venue',
            name='address',
            field=models.TextField(max_length=200),
        ),
    ]
