"""
Page models for the CMS
"""
import json

from django.db import models
from django.http.response import Http404
from django.utils.text import slugify
from wagtail.admin.edit_handlers import FieldPanel, StreamFieldPanel
from wagtail.core.fields import RichTextField, StreamField
from wagtail.core.models import Page
from wagtail.core.utils import WAGTAIL_APPEND_SLASH
from wagtail.images.edit_handlers import ImageChooserPanel
from wagtail.images.models import Image

from cms.blocks import ResourceBlock, InstructorSectionBlock
from main.views import _serialize_js_settings


class BootcampPage(Page):
    """
    CMS page representing a Bootcamp Page
    """

    class Meta:
        abstract = True

    description = RichTextField(
        blank=True, help_text="The description shown on the page."
    )
    subhead = models.CharField(
        max_length=255,
        help_text="The subhead to display in the header section on the page.",
    )
    header_image = models.ForeignKey(
        Image,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Header image size must be at least 1900x650 pixels.",
    )
    thumbnail_image = models.ForeignKey(
        Image,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Thumbnail size must be at least 690x530 pixels.",
    )
    content_panels = [
        FieldPanel("title", classname="full"),
        FieldPanel("subhead", classname="full"),
        FieldPanel("description", classname="full"),
        ImageChooserPanel("header_image"),
        ImageChooserPanel("thumbnail_image"),
    ]

    subpage_types = [
        "InstructorsPage",
    ]

    def get_context(self, request, *args, **kwargs):
        return {
            **super().get_context(request),
            "js_settings_json": json.dumps(_serialize_js_settings(request)),
            "title": self.title,
        }

    def _get_child_page_of_type(self, cls):
        """Gets the first child page of the given type if it exists"""
        child = self.get_children().type(cls).live().first()
        return child.specific if child else None

    @property
    def instructors(self):
        """Gets the faculty members page"""
        return self._get_child_page_of_type(InstructorsPage)


class BootcampRunPage(BootcampPage):
    """
    CMS page representing a bootcamp run
    """

    template = "product_page.html"

    bootcamp_run = models.OneToOneField(
        "klasses.BootcampRun",
        null=True,
        on_delete=models.SET_NULL,
        help_text="The bootcamp run for this page",
    )

    content_panels = BootcampPage.content_panels + [FieldPanel("bootcamp_run")]

    def get_context(self, request, *args, **kwargs):
        """
        return page context.
        """
        context = super().get_context(request)
        return context

    def save(self, *args, **kwargs):
        # autogenerate a unique slug so we don't hit a ValidationError
        if not self.title:
            self.title = self.__class__._meta.verbose_name.title()
        self.slug = slugify("bootcamp-{}".format(self.bootcamp_run.run_key))
        super().save(*args, **kwargs)


class ResourcePage(Page):
    """
    Basic resource page for all resource page.
    """
    template = "resource_template.html"

    sub_heading = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        help_text="Sub heading of the resource page.",
    )

    content = StreamField(
        [("content", ResourceBlock())],
        blank=False,
        help_text="Enter details of content.",
    )

    content_panels = Page.content_panels + [
        FieldPanel("sub_heading"),
        StreamFieldPanel("content"),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request)

        return context


class BootcampRunChildPage(Page):
    """
    Abstract page representing a child of BootcampRun Page
    """

    class Meta:
        abstract = True

    parent_page_types = ["BootcampRunPage"]

    # disable promote panels, no need for slug entry, it will be autogenerated
    promote_panels = []

    @classmethod
    def can_create_at(cls, parent):
        # You can only create one of these page under bootcamp.
        return (
            super().can_create_at(parent)
            and parent.get_children().type(cls).count() == 0
        )

    def save(self, *args, **kwargs):
        # autogenerate a unique slug so we don't hit a ValidationError
        if not self.title:
            self.title = self.__class__._meta.verbose_name.title()
        self.slug = slugify("{}-{}".format(self.get_parent().id, self.title))
        super().save(*args, **kwargs)

    def get_url_parts(self, request=None):
        """
        Override how the url is generated for bootcamp run child pages
        """
        # Verify the page is routable
        url_parts = super().get_url_parts(request=request)

        if not url_parts:
            return None

        site_id, site_root, parent_path = self.get_parent().specific.get_url_parts(
            request=request
        )
        page_path = ""

        # Depending on whether we have trailing slashes or not, build the correct path
        if WAGTAIL_APPEND_SLASH:
            page_path = "{}{}/".format(parent_path, self.slug)
        else:
            page_path = "{}/{}".format(parent_path, self.slug)
        return (site_id, site_root, page_path)

    def serve(self, request, *args, **kwargs):
        """
        As the name suggests these pages are going to be children of some other page. They are not
        designed to be viewed on their own so we raise a 404 if someone tries to access their slug.
        """
        raise Http404


class InstructorsPage(BootcampRunChildPage):
    """
    InstructorsPage representing a "Your MIT Instructors" section on a product page
    """

    sections = StreamField(
        [("section", InstructorSectionBlock())],
        help_text="The instructor to display in this section",
    )
    content_panels = [
        StreamFieldPanel("sections"),
    ]
