# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-05-12 15:56
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('klasses', '0005_installment_changes'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AutomaticReminderEmail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reminder_type', models.CharField(choices=[('payment_approaching', 'payment_approaching')], default='payment_approaching', max_length=30)),
                ('days_before', models.SmallIntegerField()),
                ('email_subject', models.TextField(blank=True)),
                ('email_body', models.TextField(blank=True)),
                ('sender_name', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='SentAutomaticEmails',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('automatic_email', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mail.AutomaticReminderEmail')),
                ('klass', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='klasses.Klass')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]