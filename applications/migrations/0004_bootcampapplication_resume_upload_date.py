# Generated by Django 2.2.10 on 2020-05-11 15:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("applications", "0003_move_review_fields")]

    operations = [
        migrations.AddField(
            model_name="bootcampapplication",
            name="resume_upload_date",
            field=models.DateTimeField(blank=True, null=True),
        )
    ]
