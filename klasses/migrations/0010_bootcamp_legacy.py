# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-12-13 18:23
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("klasses", "0009_personal_price")]

    operations = [
        migrations.AddField(
            model_name="bootcamp",
            name="legacy",
            field=models.BooleanField(default=True),
        )
    ]
