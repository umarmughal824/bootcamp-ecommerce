# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-05-02 15:41
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ecommerce', '0002_rename_klass'),
    ]

    operations = [
        migrations.RenameField(
            model_name='line',
            old_name='klass_id',
            new_name='klass_key',
        ),
    ]