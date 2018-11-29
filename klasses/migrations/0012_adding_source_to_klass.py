# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2018-11-09 22:05
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('klasses', '0011_bootcamp_legacy_default_false'),
    ]

    operations = [
        migrations.AddField(
            model_name='klass',
            name='source',
            field=models.CharField(choices=[('SMApply', 'SMApply'), ('FluidRev', 'FluidRev')], default='FluidRev', max_length=10),
        ),
        migrations.AlterField(
            model_name='klass',
            name='klass_key',
            field=models.IntegerField(),
        ),
        migrations.AlterUniqueTogether(
            name='klass',
            unique_together=set([('klass_key', 'source')]),
        ),
    ]
