# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-05-16 15:19
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('klasses', '0005_installment_changes'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='installment',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='installment',
            name='installment_number',
        ),
    ]
