# Generated by Django 2.2.13 on 2020-06-26 14:54

from django.db import migrations
import django_fsm


class Migration(migrations.Migration):

    dependencies = [("applications", "0013_applicantletter_types")]

    operations = [
        migrations.AlterField(
            model_name="bootcampapplication",
            name="state",
            field=django_fsm.FSMField(
                choices=[
                    ("AWAITING_PROFILE_COMPLETION", "AWAITING_PROFILE_COMPLETION"),
                    ("AWAITING_RESUME", "AWAITING_RESUME"),
                    ("AWAITING_USER_SUBMISSIONS", "AWAITING_USER_SUBMISSIONS"),
                    ("AWAITING_SUBMISSION_REVIEW", "AWAITING_SUBMISSION_REVIEW"),
                    ("AWAITING_PAYMENT", "AWAITING_PAYMENT"),
                    ("COMPLETE", "COMPLETE"),
                    ("REJECTED", "REJECTED"),
                    ("REFUNDED", "REFUNDED"),
                ],
                default="AWAITING_PROFILE_COMPLETION",
                max_length=50,
            ),
        )
    ]
