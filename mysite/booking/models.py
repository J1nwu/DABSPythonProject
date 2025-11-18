from datetime import datetime

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

class DoctorProfile(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
        ("Active", "Active"),
        ("Inactive", "Inactive"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    registration_no = models.CharField(max_length=50)
    specialization = models.CharField(max_length=80)
    experience_years = models.PositiveIntegerField(default=0)
    hospital = models.CharField(max_length=120)
    city = models.CharField(max_length=80)
    slot_preference = models.CharField(max_length=120)
    fee = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    bio = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')

    created_at = models.DateTimeField(auto_now_add=True)
    working_days = models.CharField(max_length=100, blank=True)  # e.g. "Mon–Fri"
    clinic_start_time = models.TimeField(null=True, blank=True)
    clinic_end_time = models.TimeField(null=True, blank=True)
    break_start_time = models.TimeField(null=True, blank=True)
    break_end_time = models.TimeField(null=True, blank=True)
    slot_minutes = models.PositiveIntegerField(null=True, blank=True)
    schedule_notes = models.TextField(blank=True)
    schedule_published = models.BooleanField(default=False)

    def __str__(self):
        return f"Dr. {self.user.first_name} {self.user.last_name} — {self.specialization}"

# -------------------------------------------------
# 2. Appointment  (connects Patient ↔ Doctor)
# -------------------------------------------------

from typing import Any
from django.db import models
from django.contrib.auth.models import User

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
        'DoctorProfile',
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
