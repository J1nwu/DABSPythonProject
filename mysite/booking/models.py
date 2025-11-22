from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import User
from django.db import models

class DoctorProfile(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
        ('Rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    registration_no = models.CharField(max_length=50)
    specialization = models.CharField(max_length=80)
    experience_years = models.PositiveIntegerField(default=0)
    hospital = models.CharField(max_length=120)
    city = models.CharField(max_length=80)
    slot_preference = models.CharField(max_length=120)

    fee = models.DecimalField(max_digits=8, decimal_places=2,
                              null=True, blank=True)
    bio = models.TextField()

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='Pending',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # Schedule fields used on doctor_schedule page
    working_days = models.CharField(max_length=100, blank=True)
    clinic_start_time = models.TimeField(null=True, blank=True)
    clinic_end_time = models.TimeField(null=True, blank=True)
    break_start_time = models.TimeField(null=True, blank=True)
    break_end_time = models.TimeField(null=True, blank=True)
    slot_minutes = models.PositiveIntegerField(null=True, blank=True)
    schedule_notes = models.TextField(blank=True)
    schedule_published = models.BooleanField(default=False)

    # Admin review fields used in admin_pending_doctors
    review_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_doctors',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        full_name = self.user.get_full_name() or self.user.username
        return f"Dr. {full_name} — {self.specialization}"

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rescheduled', 'Rescheduled'),
        ('Cancelled', 'Cancelled'),
        ('Completed', 'Completed'),
        ('Rejected', 'Rejected'),
    ]

    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='patient_appointments',
    )
    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name='doctor_appointments',
    )

    department = models.CharField(max_length=100)
    hospital = models.CharField(max_length=120)
    date = models.DateField()
    time = models.TimeField()
    symptoms = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.patient.username} → Dr. {self.doctor.user.last_name} ({self.status})"

from django.conf import settings

class SecurityLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def str(self):
        return f"{self.timestamp} - {self.user} - {self.action}"

# --- System-wide admin settings (single row) --------------------
from django.db import models
from django.contrib.auth.models import User


class SystemSetting(models.Model):
    """
    Simple key settings for the whole DABS system.
    We will usually keep exactly ONE row (id = 1).
    """
    site_name = models.CharField(max_length=80, default="DABS")
    hospital_name = models.CharField(max_length=120, blank=True)
    support_email = models.EmailField(blank=True)
    support_phone = models.CharField(max_length=40, blank=True)

    default_slot_minutes = models.PositiveIntegerField(default=15)
    allow_patient_registration = models.BooleanField(default=True)
    allow_doctor_registration = models.BooleanField(default=True)
    maintenance_mode = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="settings_updates",
    )

    def __str__(self):
        return f"System Settings ({self.site_name})"

class SystemLog(models.Model):
    EVENT_TYPES = [
        ("login", "User login"),
        ("logout", "User logout"),
        ("login_failed", "User login failed"),
        ("user_created", "User created"),
        ("appointment_created", "Appointment created"),
        ("appointment_updated", "Appointment updated"),
        ("appointment_deleted", "Appointment deleted"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="system_logs",
    )
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    message = models.TextField()

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        username = self.user.username if self.user else "system"
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.event_type} ({username})"

from django.conf import settings
from django.db import models

# ... your existing models (DoctorProfile, Appointment, SystemSetting, etc.) ...

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    Simple per-user in-site notification.
    Used for: appointment booked/approved/cancelled/rescheduled etc.
    NOT used for password-reset mails.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    message = models.CharField(max_length=255)

    # Optional internal link (e.g. /dashboard/patient/appointments/)
    link = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional path inside the site",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def str(self) -> str:
        return f"Notification for {self.user.username} - {self.message[:40]}"

class Feedback(models.Model):
        """
        Feedback from patient about an appointment / doctor.
        Only allowed for completed appointments.
        """
        appointment = models.OneToOneField(
            "Appointment",
            on_delete=models.CASCADE,
            related_name="feedback",
        )
        patient = models.ForeignKey(
            settings.AUTH_USER_MODEL,
            on_delete=models.CASCADE,
            related_name="feedbacks",
        )
        doctor = models.ForeignKey(
            "DoctorProfile",
            on_delete=models.CASCADE,
            related_name="feedbacks",
        )
        rating = models.PositiveSmallIntegerField(default=5)  # 1–5
        comments = models.TextField(blank=True)
        created_at = models.DateTimeField(auto_now_add=True)

        class Meta:
            ordering = ["-created_at"]

        def str(self):
            return f"Feedback {self.rating}/5 for {self.doctor} by {self.patient}"