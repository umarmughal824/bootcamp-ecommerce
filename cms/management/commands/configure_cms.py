"""Setup all CMS related stuff (home page, catalog etc.)"""
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from wagtail.core.models import Site, Page

from cms.models import HomePage

HOME_PAGE_SLUG = "home"
DEFAULT_WAGTAIL_HOMEPAGE_PROPS = dict(
    title="Welcome to your new Wagtail site!", depth=2
)
DEFAULT_HOMEPAGE_PROPS = dict(
    title="MIT Bootcamps", tagline="Learn Innovation and Entrepreneurship from MIT"
)
DEFAULT_SITE_PROPS = dict(hostname="localhost", port=80, is_default_site=True)


class Command(BaseCommand):
    """Setup all CMS related stuff (home page, catalog etc.)"""

    help = "Setup all CMS related stuff (home page, catalog etc.)"

    def add_arguments(self, parser):
        """
        Definition of arguments this command accepts
        """
        parser.add_argument(
            "--uninstall",
            action="store_true",
            help="Revert the CMS content to default structure",
        )

    def handle(self, *args, **options):
        """Setup all CMS related stuff (home page, catalog etc.)"""
        if options["uninstall"]:
            self.remove_home_page()
        else:
            self.create_home_page()

    def create_home_page(self):
        """
        Create the home page
        """
        root = Page.objects.get(depth=1)
        valid_home_page = HomePage.objects.first()
        if valid_home_page is None:
            self.stdout.write(self.style.SUCCESS("Creating home page."))
            valid_home_page = HomePage(**DEFAULT_HOMEPAGE_PROPS)
            root.add_child(instance=valid_home_page)
            valid_home_page = HomePage.objects.first()
        else:
            self.stdout.write(self.style.SUCCESS("Home page exists already."))
            valid_home_page = valid_home_page.specific
        site, _ = Site.objects.get_or_create(
            is_default_site=True,
            defaults=dict(
                root_page_id=valid_home_page.id,
                site_name=settings.WAGTAIL_SITE_NAME,
                **DEFAULT_SITE_PROPS,
            ),
        )
        if site.root_page_id != valid_home_page.id:
            self.stdout.write(self.style.SUCCESS("Settings default root page on site."))
            site.root_page_id = valid_home_page.id
            site.save()
        wagtail_default_home_page = Page.objects.filter(
            depth=2, content_type=ContentType.objects.get_for_model(Page)
        ).first()
        if wagtail_default_home_page is not None:
            self.stdout.write(self.style.SUCCESS("Moving child pages to new homepage."))
            descendants = wagtail_default_home_page.get_children()
            for descendant in descendants:
                Page.objects.get(id=descendant.id).move(valid_home_page, "last-child")
        valid_home_page.save_revision().publish()

        # Doing this at the end because if we do it earlier than
        # all changes the Site object will also get deleted along with this root.
        if wagtail_default_home_page:
            wagtail_default_home_page.delete()

    def remove_home_page(self):
        """
        Remove the home page
        """
        home_page = HomePage.objects.first()
        default_wagtail_home_page = Page.objects.filter(
            **DEFAULT_WAGTAIL_HOMEPAGE_PROPS
        ).first()
        if not default_wagtail_home_page:
            self.stdout.write(self.style.SUCCESS("Creating default home page."))
            default_wagtail_home_page = Page(**DEFAULT_WAGTAIL_HOMEPAGE_PROPS)
            root = Page.objects.get(depth=1)
            root.add_child(instance=default_wagtail_home_page)

        if home_page:
            self.stdout.write(
                self.style.SUCCESS("Moving child pages under default home page.")
            )
            descendants = home_page.get_children()
            for descendant in descendants:
                Page.objects.get(id=descendant.id).move(
                    default_wagtail_home_page, "last-child"
                )
        site = Site.objects.filter(is_default_site=True).first()
        if site:
            self.stdout.write(self.style.SUCCESS("Settings default root page on site."))
            site.root_page = default_wagtail_home_page
            site.save()
        default_wagtail_home_page.save_revision().publish()
        if home_page:
            home_page.delete()
