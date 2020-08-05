"""Tasks for applications"""
import logging
from datetime import timedelta

from django.conf import settings
from django.db.models import Q

from applications.constants import AppStates, SUBMISSION_STATUS_PENDING
from applications.models import (
    BootcampApplication,
    ApplicationStepSubmission,
    VideoInterviewSubmission,
)
from applications import api
from main.celery import app
from main.utils import now_in_utc

log = logging.getLogger()


@app.task
def create_and_send_applicant_letter(application_id, *, letter_type):
    """Create and send an applicant letter"""
    from applications import mail_api

    application = BootcampApplication.objects.get(id=application_id)
    mail_api.create_and_send_applicant_letter(application, letter_type=letter_type)


@app.task
def populate_interviews_in_jobma(application_id):
    """Create an interview in Jobma and update our models with a link to the Jobma interview"""
    application = BootcampApplication.objects.get(id=application_id)
    api.populate_interviews_in_jobma(application)


@app.task
def refresh_pending_interview_links():
    """ Recreate old pending interviews """
    now = now_in_utc()
    cutoff_date = now - timedelta(days=settings.JOBMA_LINK_EXPIRATION_DAYS)
    for submission in (
        ApplicationStepSubmission.objects.select_related("bootcamp_application")
        .exclude(
            Q(
                bootcamp_application__state__in=(
                    AppStates.AWAITING_PAYMENT,
                    AppStates.COMPLETE,
                    AppStates.REJECTED,
                    AppStates.REFUNDED,
                )
            )
            | Q(bootcamp_application__bootcamp_run__start_date__lte=now)
        )
        .filter(
            Q(submission_status=SUBMISSION_STATUS_PENDING)
            & Q(videointerviews__created_on__lte=cutoff_date)
        )
    ):
        submission.content_object.interview.delete()
        api.populate_interviews_in_jobma(submission.bootcamp_application)
        log.debug(
            f"Interview recreated for submission {submission.id}, "
            f"application {submission.bootcamp_application.id}, "
            f"user {submission.bootcamp_application.user.email}"
        )
