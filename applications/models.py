"""Models for bootcamp applications"""
from uuid import uuid4
from functools import reduce
from operator import or_

from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django_fsm import FSMField

from applications.constants import (
    SubmissionTypes,
    VALID_SUBMISSION_TYPE_CHOICES,
    AppStates,
    VALID_APP_STATE_CHOICES,
    VALID_REVIEW_STATUS_CHOICES
)
from main.models import TimestampedModel


class ApplicationStep(models.Model):
    """Defines a stage in a bootcamp application for which users must submit/upload something"""
    bootcamp = models.ForeignKey(
        'klasses.Bootcamp',
        on_delete=models.CASCADE,
        related_name='application_steps'
    )
    step_order = models.PositiveSmallIntegerField(default=1)
    submission_type = models.CharField(
        choices=VALID_SUBMISSION_TYPE_CHOICES, max_length=30
    )

    class Meta:
        unique_together = ["bootcamp", "step_order"]
        ordering = ["bootcamp", "step_order"]

    def __str__(self):
        return f"bootcamp='{self.bootcamp.title}', step={self.step_order}, type={self.submission_type}"


class BootcampRunApplicationStep(models.Model):
    """
    Defines a due date and other metadata for a bootcamp application step as it applies to a specific run
    of that bootcamp
    """
    application_step = models.ForeignKey(
        ApplicationStep,
        on_delete=models.CASCADE,
        related_name='run_steps'
    )
    bootcamp_run = models.ForeignKey(
        'klasses.Klass',
        on_delete=models.CASCADE,
        related_name='application_steps'
    )
    due_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return (
            f"run='{self.bootcamp_run.title}', step={self.application_step.step_order}, "
            f"due={self.due_date.strftime('%m/%d/%Y')}"
        )


def _get_resume_upload_path(instance, filename):
    """
    Produces the file path for an uploaded resume

    Return:
         str: The file path
    """
    return f"resumes/{instance.user.id}/{uuid4()}_{filename}"


class BootcampApplication(TimestampedModel):
    """A user's application to a run of a bootcamp"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bootcamp_applications'
    )
    bootcamp_run = models.ForeignKey(
        'klasses.Klass',
        on_delete=models.CASCADE,
        related_name='applications'
    )
    resume_file = models.FileField(upload_to=_get_resume_upload_path, null=True)
    order = models.ForeignKey(
        'ecommerce.Order',
        on_delete=models.CASCADE,
        related_name='applications',
        null=True,
        blank=True
    )
    state = FSMField(default=AppStates.AWAITING_PROFILE_COMPLETION.value, choices=VALID_APP_STATE_CHOICES)

    def __str__(self):
        return f"user='{self.user.email}', run='{self.bootcamp_run.title}', state={self.state}"


class SubmissionTypeModel(TimestampedModel):
    """Base model for any type of submission that is required on a user's bootcamp application"""
    submission_type = None

    submitted_date = models.DateTimeField(null=True, blank=True)
    review_status = models.CharField(max_length=20, choices=VALID_REVIEW_STATUS_CHOICES, null=True, blank=True)
    review_status_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


def _get_video_file_path(instance, filename):  # pylint: disable=unused-argument
    """
    Produces the file path for an uploaded video interview

    Return:
         str: The file path
    """
    return f"video_interviews/{uuid4()}_{filename}"


class VideoInterviewSubmission(SubmissionTypeModel):
    """A video interview that was submitted for review in a bootcamp application"""
    submission_type = SubmissionTypes.VIDEO_INTERVIEW.value
    app_step_submissions = GenericRelation(
        "applications.ApplicationStepSubmission",
        related_query_name="videointerviews"
    )

    video_file = models.FileField(upload_to=_get_video_file_path, null=True, blank=True)


class QuizSubmission(SubmissionTypeModel):
    """A quiz that was submitted for review in a bootcamp application"""
    submission_type = SubmissionTypes.QUIZ.value
    app_step_submissions = GenericRelation(
        "applications.ApplicationStepSubmission",
        related_query_name="quizzes"
    )

    started_date = models.DateTimeField(null=True, blank=True)


APP_SUBMISSION_MODELS = [VideoInterviewSubmission, QuizSubmission]


class ApplicationStepSubmission(TimestampedModel):
    """An item that was uploaded/submitted for review by a user as part of their bootcamp application"""
    bootcamp_application = models.ForeignKey(
        BootcampApplication,
        on_delete=models.CASCADE,
        related_name='submissions'
    )
    run_application_step = models.ForeignKey(
        BootcampRunApplicationStep,
        on_delete=models.CASCADE,
        related_name='submissions'
    )
    # This limits the choice of content type to models we have specified as application submission models
    valid_submission_types = reduce(
        or_,
        (
            models.Q(app_label="applications", model=model_cls._meta.model_name)
            for model_cls in APP_SUBMISSION_MODELS
        )  # pylint: disable=protected-access
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=valid_submission_types,
        help_text="The type of submission",
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    def __str__(self):
        return (
            f"user='{self.bootcamp_application.user.email}', run='{self.bootcamp_application.bootcamp_run.title}', "
            f"contenttype={self.content_type}, object={self.object_id}"
        )