# Generated by Django 2.2.13 on 2020-06-23 12:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("wagtailimages", "0001_squashed_0021"),
        ("cms", "0020_home_catalog_section"),
    ]

    operations = [
        migrations.RemoveField(model_name="resourcepage", name="sub_heading"),
        migrations.AddField(
            model_name="resourcepage",
            name="header_image",
            field=models.ForeignKey(
                help_text="Upload a header image that will render in the resource page.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="wagtailimages.Image",
            ),
        ),
    ]
