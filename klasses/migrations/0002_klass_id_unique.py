# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-04-13 19:23
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('klasses', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='klass',
            name='klass_id',
            field=models.IntegerField(unique=True),
        ),
    ]