# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-05-02 15:06
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('klasses', '0002_klass_id_unique'),
    ]

    operations = [
        migrations.RenameField(
            model_name='klass',
            old_name='klass_id',
            new_name='klass_key',
        ),
    ]
