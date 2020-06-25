# Generated by Django 2.2.10 on 2020-06-18 14:46

from django.db import migrations, models
import django.db.models.deletion


def delete_line_resync(apps, schema_editor):
    """
    Delete any existing HubspotLineResync objects
    """
    HubspotLineResync = apps.get_model("hubspot", "HubspotLineResync")
    HubspotLineResync.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("applications", "0010_add_waitlisted_status"),
        ("hubspot", "0002_hubspotlineresync"),
    ]

    operations = [
        migrations.RunPython(delete_line_resync, delete_line_resync),
        migrations.RemoveField(model_name="hubspotlineresync", name="personal_price"),
        migrations.AddField(
            model_name="hubspotlineresync",
            name="application",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="applications.BootcampApplication",
            ),
        ),
        migrations.RunPython(delete_line_resync, delete_line_resync),
    ]
