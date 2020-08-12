# Generated by Django 2.2.13 on 2020-08-18 11:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [("cms", "0026_add_signatory_fields_letter_template_page")]

    operations = [
        migrations.AlterField(
            model_name="lettertemplatepage",
            name="signature_image",
            field=models.ForeignKey(
                blank=True,
                help_text="Upload an image that will render in the program description section.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="wagtailimages.Image",
            ),
        )
    ]
