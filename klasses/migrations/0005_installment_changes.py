# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-05-15 16:35
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("klasses", "0004_admission_cache")]

    operations = [
        migrations.AlterModelOptions(
            name="installment", options={"ordering": ["klass", "deadline"]}
        ),
        migrations.AlterField(
            model_name="installment", name="deadline", field=models.DateTimeField()
        ),
    ]
