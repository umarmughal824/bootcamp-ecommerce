# Generated by Django 2.2.10 on 2020-06-02 20:52

from django.db import migrations, models

from applications.models import REVIEW_STATUS_PENDING


def update_null_review_status(apps, schema_editor):
    """Update ApplicationStepSubmission that are currently pending"""
    ApplicationStepSubmission = apps.get_model(
        "applications", "ApplicationStepSubmission"
    )

    ApplicationStepSubmission.objects.filter(review_status__isnull=True).update(
        review_status=REVIEW_STATUS_PENDING
    )


def reverse_update_null_review_status(apps, schema_editor):
    """Rollback the changes from update_null_review_status()"""
    ApplicationStepSubmission = apps.get_model(
        "applications", "ApplicationStepSubmission"
    )

    ApplicationStepSubmission.objects.filter(
        review_status=REVIEW_STATUS_PENDING
    ).update(review_status=None)


class Migration(migrations.Migration):

    dependencies = [("applications", "0008_bootcampapplication_linkedin_url")]

    operations = [
        migrations.AlterField(
            model_name="applicationstepsubmission",
            name="review_status",
            field=models.CharField(
                choices=[
                    ("pending", "pending"),
                    ("approved", "approved"),
                    ("rejected", "rejected"),
                ],
                default="pending",
                max_length=20,
                null=True,
            ),
        ),
        migrations.RunPython(
            update_null_review_status, reverse_update_null_review_status
        ),
        migrations.AlterField(
            model_name="applicationstepsubmission",
            name="review_status",
            field=models.CharField(
                choices=[
                    ("pending", "pending"),
                    ("approved", "approved"),
                    ("rejected", "rejected"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]
