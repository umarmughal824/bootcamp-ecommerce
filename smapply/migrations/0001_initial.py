# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2018-11-15 16:14
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='OAuthTokenSMA',
            fields=[
                ('id', models.IntegerField(default=1, primary_key=True, serialize=False, unique=True)),
                ('access_token', models.TextField(null=True)),
                ('refresh_token', models.TextField(null=True)),
                ('token_type', models.CharField(default='Bearer', max_length=30)),
                ('expires_on', models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name='WebhookRequestSMA',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('body', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('Created', 'Created'), ('Failed', 'Failed'), ('Succeeded', 'Succeeded')], default='Created', max_length=10)),
                ('user_id', models.IntegerField(blank=True, null=True)),
                ('submission_id', models.IntegerField(blank=True, null=True)),
                ('award_id', models.IntegerField(blank=True, null=True)),
                ('award_title', models.CharField(blank=True, max_length=512)),
            ],
            options={
                'ordering': ['award_id', 'created_on'],
            },
        ),
    ]
