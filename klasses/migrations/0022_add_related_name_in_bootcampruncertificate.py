# Generated by Django 2.2.13 on 2020-12-23 11:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [("klasses", "0021_bootcampruncertificate")]

    operations = [
        migrations.AlterField(
            model_name="bootcampruncertificate",
            name="bootcamp_run",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="certificates",
                to="klasses.BootcampRun",
            ),
        )
    ]
