from django.contrib.auth.models import User
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .models import Appointment
from .utils import log_event


# ---------- USER EVENTS ----------


@receiver(post_save, sender=User)
def log_user_created(sender, instance: User, created: bool, **kwargs):
    """
    Logs when a new user is created (patient, doctor, or admin).
    """
    if created:
        log_event(
            event_type="user_created",
            message=f"New user registered: {instance.username}",
            user=instance,
        )


@receiver(user_logged_in)
def log_user_login(sender, request, user: User, **kwargs):
    log_event(
        event_type="login",
        message=f"User logged in: {user.username}",
        user=user,
        request=request,
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user: User, **kwargs):
    log_event(
        event_type="logout",
        message=f"User logged out: {user.username}",
        user=user,
        request=request,
    )


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    username = credentials.get("username") or "unknown"
    log_event(
        event_type="login_failed",
        message=f"Failed login attempt for username: {username}",
        user=None,
        request=request,
    )


# ---------- APPOINTMENT EVENTS ----------


@receiver(post_save, sender=Appointment)
def log_appointment_save(sender, instance: Appointment, created: bool, **kwargs):
    """
    Logs creation and updates (status change, reschedule, etc.) of appointments.
    """
    patient_username = instance.patient.username if instance.patient else "unknown"
    doctor_name = (
        f"Dr. {instance.doctor.user.get_full_name()}"
        if instance.doctor and instance.doctor.user
        else "Unknown doctor"
    )

    if created:
        msg = (
            f"Appointment #{instance.id} created: "
            f"{patient_username} → {doctor_name} on {instance.date} at {instance.time} "
            f"(status={instance.status})."
        )
        log_event(
            event_type="appointment_created",
            message=msg,
            user=instance.patient,
        )
    else:
        msg = (
            f"Appointment #{instance.id} updated: "
            f"{patient_username} → {doctor_name}, "
            f"date={instance.date}, time={instance.time}, status={instance.status}."
        )
        log_event(
            event_type="appointment_updated",
            message=msg,
            user=instance.patient,
        )


@receiver(pre_delete, sender=Appointment)
def log_appointment_deleted(sender, instance: Appointment, **kwargs):
    patient_username = instance.patient.username if instance.patient else "unknown"
    msg = (
        f"Appointment #{instance.id} deleted: "
        f"{patient_username} → Dr. {instance.doctor.user.get_full_name() if instance.doctor and instance.doctor.user else 'Unknown'}."
    )
    log_event(
        event_type="appointment_deleted",
        message=msg,
        user=instance.patient,
    )

