"""
Wagtail custom blocks for the CMS
"""
from wagtail.core import blocks
from wagtail.images.blocks import ImageChooserBlock


class ResourceBlock(blocks.StructBlock):
    """
    A custom block for resource pages.
    """

    heading = blocks.CharBlock(max_length=100)
    detail = blocks.RichTextBlock()


class InstructorBlock(blocks.StructBlock):
    """
    Block class that defines a instructor
    """

    name = blocks.CharBlock(max_length=100, help_text="Name of the instructor.")
    image = ImageChooserBlock(
        help_text="Profile image size must be at least 300x300 pixels."
    )
    title = blocks.CharBlock(
        max_length=255, help_text="A brief description about the instructor."
    )


class InstructorSectionBlock(blocks.StructBlock):
    """
    Block class that defines a instrcutors section
    """

    heading = blocks.CharBlock(
        max_length=255, help_text="The heading to display for this section on the page."
    )
    subhead = blocks.RichTextBlock(
        help_text="The subhead to display for this section on the page."
    )
    heading_singular = blocks.CharBlock(
        max_length=100, help_text="Heading that will highlight the instructor point."
    )
    members = blocks.StreamBlock(
        [("member", InstructorBlock())],
        help_text="The instructors to display in this section",
    )


class ThreeColumnImageTextBlock(blocks.StructBlock):
    """
    A generic custom block used to input heading, sub-heading, body and image.
    """

    heading = blocks.CharBlock(
        max_length=100, help_text="Heading that will highlight the main point."
    )
    sub_heading = blocks.CharBlock(max_length=250, help_text="Area sub heading.")
    body = blocks.RichTextBlock()
    image = ImageChooserBlock(help_text="image size must be at least 150x50 pixels.")

    class Meta:
        icon = "plus"


class AlumniBlock(blocks.StructBlock):
    """
    Block class that defines alumni section
    """

    image = ImageChooserBlock(help_text="The image of the alumni")
    name = blocks.CharBlock(max_length=100, help_text="Name of the alumni.")
    title = blocks.CharBlock(
        max_length=255, help_text="The title to display after the name."
    )
    class_text = blocks.CharBlock(
        max_length=100, help_text="A brief description about the alumni class."
    )
    quote = blocks.RichTextBlock(
        help_text="The quote that appears on the alumni section."
    )


class TitleLinksBlock(blocks.StructBlock):
    """
    Block class that contains learning resources
    """

    title = blocks.CharBlock(
        max_length=100, help_text="The title to display for this section on the page."
    )
    links = blocks.RichTextBlock(
        help_text="Represent resources with the links to display. Add each link in the new line of the editor."
    )


class TitleDescriptionBlock(blocks.StructBlock):
    """
    A generic custom block used to input title and description.
    """

    title = blocks.CharBlock(
        max_length=100, help_text="Title that will highlight the main point."
    )
    description = blocks.RichTextBlock()

    class Meta:
        icon = "plus"
