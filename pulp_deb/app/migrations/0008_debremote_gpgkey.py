# Generated by Django 2.2.10 on 2020-02-17 12:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('deb', '0007_create_metadata_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='debremote',
            name='gpgkey',
            field=models.TextField(null=True),
        ),
    ]
