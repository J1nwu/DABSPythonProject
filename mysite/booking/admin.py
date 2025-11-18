from django.contrib import admin
from .models import DoctorProfile, Appointment, Notification, SecurityLog

@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "specialization", "hospital", "city", "status", "experience_years")
    list_filter = ("status", "city", "specialization")
    search_fields = ("user__first_name", "user__last_name", "registration_no",
                     "specialization", "hospital", "city")

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "department", "hospital", "date", "time", "status")
    list_filter = ("status", "hospital", "department", "date")
    search_fields = ("patient__username", "doctor__user__username", "department", "hospital")

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "created_at", "is_read")
    list_filter = ("is_read", "created_at")
    search_fields = ("user__username", "message")

@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user", "action")
    search_fields = ("user", "action")
