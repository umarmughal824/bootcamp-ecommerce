"""
klasses API tests
"""

import pytest

from klasses.api import deactivate_run_enrollment, fetch_bootcamp_run
from klasses.constants import ENROLL_CHANGE_STATUS_REFUNDED
from klasses.factories import BootcampRunEnrollmentFactory
from klasses.factories import BootcampRunFactory
from klasses.models import BootcampRun

pytestmark = pytest.mark.django_db


def test_deactivate_run_enrollment():
    """Test that deactivate_run_enrollment updates enrollment fields correctly"""
    enrollment = BootcampRunEnrollmentFactory.create()
    deactivate_run_enrollment(enrollment, ENROLL_CHANGE_STATUS_REFUNDED)
    assert enrollment.active is False
    assert enrollment.change_status == ENROLL_CHANGE_STATUS_REFUNDED


@pytest.mark.django_db
def test_fetch_bootcamp_run():
    """fetch_bootcamp_run should fetch a bootcamp run with a field value that matches the given property"""
    title = "Run 1"
    run = BootcampRunFactory.create(title=title)
    assert fetch_bootcamp_run(str(run.id)) == run
    assert fetch_bootcamp_run(title) == run
    with pytest.raises(BootcampRun.DoesNotExist):
        fetch_bootcamp_run("invalid")
