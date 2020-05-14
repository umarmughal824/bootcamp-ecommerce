# Generated by Django 2.2.10 on 2020-05-11 17:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0005_application_multiple_orders'),
        ('ecommerce', '0004_rename_klass_to_bootcamp_run'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='application',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='orders', to='applications.BootcampApplication'),
        ),
    ]
