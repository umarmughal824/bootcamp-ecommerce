"""Utility functions for Klasses"""

from klasses.models import BootcampRunCertificate, BootcampRunEnrollment


def generate_single_certificate(user, bootcamp_run):
    """Generates certificate for a single user if its enrollment is active"""
    result = {"updated": False}
    if user and bootcamp_run:
        certificate = BootcampRunCertificate.all_objects.filter(
            user=user, bootcamp_run=bootcamp_run
        ).first()
        if certificate:
            result[
                "msg"
            ] = "A {} certificate:{} already exists for user:{} in bootcamp-run:{}".format(
                "revoked" if certificate.is_revoked else "",
                certificate.link,
                user.email,
                bootcamp_run,
            )
        elif BootcampRunEnrollment.objects.filter(
            user=user, bootcamp_run=bootcamp_run, active=True
        ).exists():
            certificate = BootcampRunCertificate.objects.create(
                user=user, bootcamp_run=bootcamp_run
            )
            result.update(
                {
                    "updated": True,
                    "msg": "A certificate:{} has been generated for user:{} in bootcamp-run:{}".format(
                        certificate.link, user.email, bootcamp_run
                    ),
                }
            )
        else:
            result[
                "msg"
            ] = "User:{} doesn't have an active enrollment in bootcamp-run:{}".format(
                user.email, bootcamp_run
            )
    else:
        result["msg"] = "Valid user and bootcamp_run must be provided."

    return result


def generate_batch_certificates(bootcamp_run):
    """Generates certificates for all the users who have active enrollments in a bootcamp-run"""
    result = {"updated": False}
    if bootcamp_run:
        certificates = BootcampRunCertificate.objects.bulk_create(
            [
                BootcampRunCertificate(user=enrollment.user, bootcamp_run=bootcamp_run)
                for enrollment in BootcampRunEnrollment.objects.filter(
                    bootcamp_run=bootcamp_run, active=True
                )
                if not BootcampRunCertificate.all_objects.filter(
                    user=enrollment.user, bootcamp_run=bootcamp_run
                ).exists()
            ],
            ignore_conflicts=True,
        )
        if len(certificates):
            result.update(
                {
                    "updated": True,
                    "msg": "{} new certificates have been created for bootcamp-run:{}".format(
                        len(certificates), bootcamp_run
                    ),
                }
            )
        else:
            result["msg"] = "No new certificates were made for bootcamp-run:{}".format(
                bootcamp_run
            )
    else:
        result["msg"] = "A valid bootcamp_run must be provided."

    return result


def revoke_certificate(user, bootcamp_run):
    """Revokes certificate for the given user and bootcamp-run"""
    result = {"updated": False}
    if user and bootcamp_run:
        certificate = BootcampRunCertificate.all_objects.filter(
            user=user, bootcamp_run=bootcamp_run
        ).first()
        if certificate:
            if not certificate.is_revoked:
                certificate.revoke()
                result.update(
                    {
                        "updated": True,
                        "msg": "Certificate:{} has been revoked for user:{} in bootcamp-run:{}".format(
                            certificate.link, user.email, bootcamp_run
                        ),
                    }
                )
            else:
                result[
                    "msg"
                ] = "Certificate:{} is already in revoked state for user:{} in bootcamp-run:{}".format(
                    certificate.link, user.email, bootcamp_run
                )
        else:
            result[
                "msg"
            ] = "No Certificate found for user:{} in bootcamp-run:{}".format(
                user.email, bootcamp_run
            )
    else:
        result["msg"] = "Valid user and bootcamp_run must be provided."

    return result


def unrevoke_certificate(user, bootcamp_run):
    """Unrevokes certificate for the given user and bootcamp-run"""
    result = {"updated": False}
    if user and bootcamp_run:
        certificate = BootcampRunCertificate.all_objects.filter(
            user=user, bootcamp_run=bootcamp_run
        ).first()
        if certificate:
            if certificate.is_revoked:
                certificate.unrevoke()
                result.update(
                    {
                        "updated": True,
                        "msg": "Certificate:{} has been unrevoked for user:{} in bootcamp-run:{}".format(
                            certificate.link, user.email, bootcamp_run
                        ),
                    }
                )
            else:
                result[
                    "msg"
                ] = "Certificate:{} is already in unrevoked state for user:{} in bootcamp-run:{}".format(
                    certificate.link, user.email, bootcamp_run
                )
        else:
            result[
                "msg"
            ] = "No Certificate found for user:{} in bootcamp-run:{}".format(
                user.email, bootcamp_run
            )
    else:
        result["msg"] = "Valid user and bootcamp_run must be provided."

    return result
