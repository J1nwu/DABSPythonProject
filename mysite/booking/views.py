from datetime import datetime

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .models import DoctorProfile, Appointment, SystemSetting

from datetime import date, datetime
from .utils import log_event
from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login,
    logout,
    get_user_model,
)
from django.contrib.auth.decorators import login_required
from django.http import (
    Http404,
    HttpResponseForbidden,
)
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from .models import DoctorProfile, Appointment, SystemSetting
from .models import SecurityLog


def log_action(user, action: str) -> None:
    """
    Write one entry into SecurityLog.
    user is a Django User instance (request.user).
    action is a short description string.
    """
    username = getattr(user, "username", str(user))
    SecurityLog.objects.create(user=user, action=action)

# ============================
# BASIC PAGES / AUTH
# ============================

def home(request):
    return render(request, "booking/home.html")


def login_user(request):
    """
    Shared login for all roles.
    After login, always go through route_after_login().
    """
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Invalid username or password.")
            return render(request, "booking/login.html", {"username": username})

        login(request, user)
        return redirect("route_after_login")

    return render(request, "booking/login.html")


def logout_user(request):
    logout(request)
    return redirect("login")


@login_required
def route_after_login(request):
    """
    Decide where to send user after successful login.
    - Staff / superuser → Admin dashboard
    - Doctor (has DoctorProfile) → Doctor dashboard
    - Everyone else → Patient dashboard
    """
    user = request.user

    if user.is_staff or user.is_superuser:
        return redirect("admin_dashboard")

    if DoctorProfile.objects.filter(user=user).exists():
        return redirect("doctor_dashboard")

    return redirect("patient_dashboard")

@login_required
def post_login_redirect(request):
    """
    Backwards-compatibility alias for old URL.
    Just reuse the main router.
    """
    return route_after_login(request)


# ============================
# PATIENT REGISTRATION / DASHBOARD
# ============================

def patient_register(request):
    """
    Patient self-registration, controlled by SystemSetting.
    """
    settings_obj, _ = SystemSetting.objects.get_or_create(pk=1)
    if not settings_obj.allow_patient_registration:
        messages.error(
            request,
            "New patient registrations are currently disabled by the administrator.",
        )
        return redirect("home")

    if request.method == "POST":
        first = request.POST.get("first_name", "").strip()
        last = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        phone = request.POST.get("phone", "").strip()  # you can store later if needed
        password = request.POST.get("password", "")
        confirm = request.POST.get("confirm_password", "")

        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return redirect("patient_register")

        if not email:
            messages.error(request, "Email is required.")
            return redirect("patient_register")

        username = email  # using email as username

        if get_user_model().objects.filter(username=username).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect("patient_register")

        UserModel = get_user_model()
        user = UserModel.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first,
            last_name=last,
        )
        user.save()
        messages.success(request, "Registration successful. Please login.")
        return redirect("login")

    return render(request, "booking/patient_register.html")


@login_required
def patient_dashboard(request):
    return render(request, "booking/patient_dashboard.html")


# ============================
# DOCTOR REGISTRATION / DASHBOARD
# ============================

def doctor_register(request):
    """
    Doctor self-registration.
    Creates User + DoctorProfile with status='Pending'.
    Registration can be disabled in SystemSetting.
    """
    settings_obj, _ = SystemSetting.objects.get_or_create(pk=1)
    if not settings_obj.allow_doctor_registration:
        messages.error(
            request,
            "New doctor registrations are currently disabled by the administrator.",
        )
        return redirect("home")

    if request.method == "POST":
        first = request.POST.get("first_name", "").strip()
        last = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        confirm = request.POST.get("confirm_password", "")

        regno = request.POST.get("registration_no", "").strip()
        spec = request.POST.get("specialization", "").strip()
        exp = request.POST.get("experience", "0").strip()
        hospital = request.POST.get("hospital", "").strip()
        city = request.POST.get("city", "").strip()
        slot = request.POST.get("slot_pref", "").strip()
        fee = request.POST.get("fee", "").strip()
        bio = request.POST.get("bio", "").strip()

        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return redirect("doctor_register")

        if not email:
            messages.error(request, "Email is required.")
            return redirect("doctor_register")

        username = email

        UserModel = get_user_model()
        if UserModel.objects.filter(username=username).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect("doctor_register")

        user = UserModel.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first,
            last_name=last,
        )

        fee_value = None
        if fee:
            try:
                fee_value = float(fee)
            except ValueError:
                fee_value = None

        DoctorProfile.objects.create(
            user=user,
            registration_no=regno,
            specialization=spec,
            experience_years=int(exp) if exp.isdigit() else 0,
            hospital=hospital,
            city=city,
            slot_preference=slot,
            fee=fee_value,
            bio=bio,
            status="Pending",
        )

        messages.success(
            request,
            "Doctor registered. Status: Pending approval. You can login after admin approval.",
        )
        return redirect("login")

    return render(request, "booking/doctor_register.html")

# ============================
# PATIENT: FIND / BOOK / MANAGE APPOINTMENTS
# ============================

@login_required
def find_doctor(request):
    q = request.GET.get("q", "").strip()
    doctors = DoctorProfile.objects.filter(status="Active")

    if q:
        doctors = doctors.filter(
            Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(specialization__icontains=q)
            | Q(hospital__icontains=q)
            | Q(city__icontains=q)
        )

    return render(
        request,
        "booking/find_doctor.html",
        {"doctors": doctors, "q": q},
    )


@login_required
def book_appointment(request, doctor_id):
    doctor = get_object_or_404(DoctorProfile, id=doctor_id, status="Active")

    if request.method == "POST":
        department = request.POST.get("department", "").strip()
        hospital = request.POST.get("hospital", "").strip()
        appt_date = request.POST.get("date", "").strip()
        appt_time = request.POST.get("time", "").strip()
        symptoms = request.POST.get("symptoms", "").strip()

        Appointment.objects.create(
            patient=request.user,
            doctor=doctor,
            department=department,
            hospital=hospital,
            date=appt_date,
            time=appt_time,
            symptoms=symptoms,
            status="Pending",
        )

        messages.success(request, "Appointment booked successfully!")
        return redirect("patient_dashboard")

    return render(
        request,
        "booking/book_appointment.html",
        {"doctor": doctor, "today": date.today()},
    )


@login_required
def my_appointments(request):
    appts = Appointment.objects.filter(patient=request.user).order_by("-date", "-time")
    return render(request, "booking/my_appointments.html", {"appts": appts})


@login_required
def cancel_appointment(request, appt_id):
    """
    Patient cancels own appointment (POST only).
    Block cancelling Completed/Cancelled; optionally past datetime.
    """
    if request.method != "POST":
        return HttpResponseForbidden("POST required")

    appt = get_object_or_404(Appointment, id=appt_id, patient=request.user)

    if appt.status in ["Completed", "Cancelled"]:
        messages.error(request, "This appointment cannot be cancelled.")
        return redirect("my_appointments")

    # Optional: block cancelling past datetime if both date and time exist
    try:
        if appt.date and appt.time:
            appt_dt = datetime.combine(appt.date, appt.time)
            appt_dt = (
                timezone.make_aware(appt_dt)
                if timezone.is_naive(appt_dt)
                else appt_dt
            )
            if appt_dt <= timezone.now():
                messages.error(request, "Past appointments cannot be cancelled.")
                return redirect("my_appointments")
    except Exception:
        pass

    appt.status = "Cancelled"
    appt.save(update_fields=["status"])
    messages.success(request, "Appointment cancelled.")
    return redirect("my_appointments")


@login_required
def reschedule_appointment(request, appt_id):
    """
    Patient reschedules own appointment.
    """
    appt = get_object_or_404(Appointment, id=appt_id, patient=request.user)

    if request.method == "GET":
        return render(request, "booking/reschedule_appointment.html", {"appt": appt})

    new_date_str = request.POST.get("date", "").strip()
    new_time_str = request.POST.get("time", "").strip()

    if not new_date_str or not new_time_str:
        messages.error(request, "Both date and time are required.")
        return redirect("reschedule_appointment", appt_id=appt.id)

    try:
        new_date_val = datetime.strptime(new_date_str, "%Y-%m-%d").date()
        new_time_val = datetime.strptime(new_time_str, "%H:%M").time()
    except ValueError:
        messages.error(request, "Invalid date or time.")
        return redirect("reschedule_appointment", appt_id=appt.id)

    new_dt = datetime.combine(new_date_val, new_time_val)
    new_dt = (
        timezone.make_aware(new_dt) if timezone.is_naive(new_dt) else new_dt
    )
    if new_dt <= timezone.now():
        messages.error(request, "Choose a future date/time.")
        return redirect("reschedule_appointment", appt_id=appt.id)

    appt.date = new_date_val
    appt.time = new_time_val
    appt.status = "Rescheduled"
    appt.save(update_fields=["date", "time", "status"])

    messages.success(request, "Appointment rescheduled.")
    return redirect("my_appointments")


# ============================
# DOCTOR: APPROVALS / SCHEDULE / APPOINTMENTS / PATIENTS
# ============================

@login_required
def doctor_dashboard(request):
    """
    Simple doctor dashboard with basic stats.
    """
    profile = get_object_or_404(DoctorProfile, user=request.user)

    today = timezone.localdate()

    today_appointments = Appointment.objects.filter(
        doctor=profile,
        date=today,
    ).count()

    pending_approvals = Appointment.objects.filter(
        doctor=profile,
        status="Pending",
    ).count()

    total_patients = (
        Appointment.objects.filter(doctor=profile)
        .values("patient_id")
        .distinct()
        .count()
    )

    context = {
        "profile": profile,
        "today_appointments": today_appointments,
        "pending_approvals": pending_approvals,
        "total_patients": total_patients,
        "section": "dashboard",
    }
    return render(request, "booking/doctor_dashboard.html", context)


@login_required
def doctor_approvals(request):
    """
    List all pending appointments for this doctor.
    """
    try:
        doctor = DoctorProfile.objects.get(user=request.user)
    except DoctorProfile.DoesNotExist:
        # If somehow a non-doctor hits this, send them to patient dashboard
        return redirect("patient_dashboard")

    pending_appointments = (
        Appointment.objects.filter(doctor=doctor, status="Pending")
        .order_by("date", "time")
    )

    return render(
        request,
        "booking/doctor_approvals.html",
        {"pending_appointments": pending_appointments},
    )


@login_required
def doctor_approve(request, appt_id):
    """
    Approve a pending appointment.
    """
    try:
        appt = Appointment.objects.get(id=appt_id, doctor__user=request.user)
    except Appointment.DoesNotExist:
        raise Http404("Appointment not found")

    appt.status = "Approved"
    appt.save(update_fields=["status"])
    messages.success(request, "Appointment approved.")
    return redirect("doctor_approvals")


@login_required
def doctor_reject(request, appt_id):
    """
    Reject a pending appointment.
    """
    try:
        appt = Appointment.objects.get(id=appt_id, doctor__user=request.user)
    except Appointment.DoesNotExist:
        raise Http404("Appointment not found")

    appt.status = "Rejected"
    appt.save(update_fields=["status"])
    messages.success(request, "Appointment rejected.")
    return redirect("doctor_approvals")


@login_required
def doctor_reschedule(request, appt_id):
    """
    Reschedule an appointment (doctor side).
    """
    try:
        appt = Appointment.objects.get(id=appt_id, doctor__user=request.user)
    except Appointment.DoesNotExist:
        raise Http404("Appointment not found")

    if request.method == "GET":
        return render(request, "booking/doctor_reschedule.html", {"appt": appt})

    # POST
    new_date = request.POST.get("date", "").strip()
    new_time = request.POST.get("time", "").strip()

    if not new_date or not new_time:
        messages.error(request, "Both date and time are required.")
        return redirect("doctor_reschedule", appt_id=appt.id)

    try:
        nd = datetime.strptime(new_date, "%Y-%m-%d").date()
        nt = datetime.strptime(new_time, "%H:%M").time()
    except ValueError:
        messages.error(request, "Invalid date/time.")
        return redirect("doctor_reschedule", appt_id=appt.id)

    appt.date = nd
    appt.time = nt
    appt.status = "Rescheduled"
    appt.save(update_fields=["date", "time", "status"])

    messages.success(request, "Appointment rescheduled.")
    return redirect("doctor_approvals")


from django.db.models import Q
from django.contrib.auth.decorators import login_required

@login_required
def doctor_appointments(request):
    """
    Doctor: view appointments with simple filters.
    Shows ALL appointments for this doctor.
    """
    try:
        doctor = DoctorProfile.objects.get(user=request.user)
    except DoctorProfile.DoesNotExist:
        return redirect("patient_dashboard")

    # Base queryset: all appts for this doctor
    qs = Appointment.objects.filter(doctor=doctor)

    # --- Filters from GET ---
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    # Text search: patient name / username / symptoms
    if q:
        qs = qs.filter(
            Q(patient__first_name__icontains=q)
            | Q(patient__last_name__icontains=q)
            | Q(patient__username__icontains=q)
            | Q(symptoms__icontains=q)
        )

    # Status filter
    if status:
        qs = qs.filter(status=status)

    appointments = qs.order_by("-date", "-time")  # newest first

    context = {
        "appointments": appointments,
        "q": q,
        "status": status,
    }
    return render(request, "booking/doctor_appointments.html", context)


@login_required
def doctor_patients(request):
    """
    Doctor: list unique patients who have appointments with this doctor.
    """
    try:
        doctor = DoctorProfile.objects.get(user=request.user)
    except DoctorProfile.DoesNotExist:
        return redirect("patient_dashboard")

    UserModel = get_user_model()

    patient_ids = (
        Appointment.objects.filter(doctor=doctor)
        .values_list("patient_id", flat=True)
        .distinct()
    )

    patients_qs = UserModel.objects.filter(id__in=patient_ids)

    q = request.GET.get("q", "").strip()
    if q:
        patients_qs = patients_qs.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(username__icontains=q)
            | Q(email__icontains=q)
        )

    # patient_appointments = related_name on Appointment.patient
    patients = (
        patients_qs
        .annotate(total_appointments=Count("patient_appointments"))
        .order_by("first_name", "last_name")
    )

    return render(
        request,
        "booking/doctor_patients.html",
        {
            "patients": patients,
            "q": q,
        },
    )


@login_required
def doctor_schedule(request):
    """
    Doctor schedule page.

    - POST: update schedule fields on DoctorProfile
    - GET: show all non-completed, non-pending, non-cancelled appointments
      for this doctor (Approved + Rescheduled only), ordered oldest first.
    """
    try:
        profile = DoctorProfile.objects.get(user=request.user)
    except DoctorProfile.DoesNotExist:
        return redirect("patient_dashboard")

    # System default slot minutes fallback
    settings_obj, _ = SystemSetting.objects.get_or_create(pk=1)
    if not profile.slot_minutes and settings_obj.default_slot_minutes:
        profile.slot_minutes = settings_obj.default_slot_minutes

    def parse_time(value: str):
        if not value:
            return None
        try:
            return datetime.strptime(value, "%H:%M").time()
        except ValueError:
            return None

    # --- UPDATE SCHEDULE (POST) ---
    if request.method == "POST":
        working_days = request.POST.get("working_days", "").strip()
        start = request.POST.get("clinic_start_time", "").strip()
        end = request.POST.get("clinic_end_time", "").strip()
        bstart = request.POST.get("break_start_time", "").strip()
        bend = request.POST.get("break_end_time", "").strip()
        slot = request.POST.get("slot_minutes", "").strip()
        notes = request.POST.get("schedule_notes", "").strip()
        published = request.POST.get("schedule_published") == "on"

        profile.working_days = working_days
        profile.clinic_start_time = parse_time(start)
        profile.clinic_end_time = parse_time(end)
        profile.break_start_time = parse_time(bstart)
        profile.break_end_time = parse_time(bend)

        if slot.isdigit():
            profile.slot_minutes = int(slot)
        else:
            profile.slot_minutes = (
                settings_obj.default_slot_minutes or profile.slot_minutes
            )

        profile.schedule_notes = notes
        profile.schedule_published = published
        profile.save()

        messages.success(request, "Schedule updated.")
        return redirect("doctor_schedule")

    # --- SCHEDULE LIST (GET) ---
    # Only appointments that are still to be done:
    # Approved + Rescheduled; everything else excluded.
    upcoming_appointments = (
        Appointment.objects
        .filter(
            doctor=profile,
            status__in=["Approved", "Rescheduled"],
        )
        .order_by("date", "time")  # oldest first
    )

    return render(
        request,
        "booking/doctor_schedule.html",
        {
            "profile": profile,
            "upcoming_appointments": upcoming_appointments,
        },
    )


# ============================
# ADMIN: DASHBOARD + DOCTOR APPLICATIONS
# ============================

@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect("home")

    UserModel = get_user_model()

    total_doctors = DoctorProfile.objects.filter(status="Active").count()
    pending_doctors = DoctorProfile.objects.filter(status="Pending").count()

    # Non-staff normal users (includes doctors, but okay for a high-level count)
    total_patients = UserModel.objects.filter(is_staff=False).count()

    today = timezone.localdate()
    todays_appointments = Appointment.objects.filter(date=today).count()

    context = {
        "total_doctors": total_doctors,
        "pending_doctors": pending_doctors,
        "total_patients": total_patients,
        "todays_appointments": todays_appointments,
        "section": "dashboard",
    }
    return render(request, "booking/admin_dashboard.html", context)


@login_required
def admin_pending_doctors(request):
    """
    Admin: list and process pending doctor applications.
    Actions: approve (→ Active) / reject (→ Inactive).
    """
    if not request.user.is_staff:
        return redirect("home")

    if request.method == "POST":
        doctor_id = request.POST.get("doctor_id")
        action = request.POST.get("action")  # 'approve' or 'reject'

        if not doctor_id or action not in ["approve", "reject"]:
            messages.error(request, "Invalid action.")
            return redirect("admin_pending_doctors")

        doc = get_object_or_404(DoctorProfile, id=doctor_id, status="Pending")
        full_name = doc.user.get_full_name() or doc.user.username

        if action == "approve":
            doc.status = "Active"
            messages.success(request, f"Doctor {full_name} approved.")
        else:
            doc.status = "Inactive"
            messages.success(request, f"Doctor {full_name} rejected.")

        doc.save(update_fields=["status"])
        return redirect("admin_pending_doctors")

    pending = (
        DoctorProfile.objects.filter(status="Pending")
        .select_related("user")
        .order_by("user__first_name", "user__last_name")
    )

    context = {
        "pending": pending,
        "section": "applications",
    }
    return render(request, "booking/admin_pending_doctors.html", context)


@login_required
def admin_doctor_applications(request):
    """
    Optional separate page just listing pending doctors (read-only).
    """
    if not request.user.is_staff:
        return redirect("home")

    pending_doctors = (
        DoctorProfile.objects.filter(status="Pending")
        .select_related("user")
        .order_by("user__first_name", "user__last_name")
    )
    return render(
        request,
        "booking/admin_doctor_applications.html",
        {"pending_doctors": pending_doctors, "section": "applications"},
    )


# ============================
# ADMIN: MANAGE DOCTORS
# ============================

@login_required
def admin_doctors(request):
    """
    Admin: Manage doctors.
    - Filter by text / status
    - Actions: Activate / Deactivate / Delete
    """
    if not request.user.is_staff:
        return redirect("home")

    # POST actions
    if request.method == "POST":
        doc_id = request.POST.get("doctor_id")
        action = request.POST.get("action")  # activate / deactivate / delete

        if doc_id and action:
            try:
                doc = DoctorProfile.objects.select_related("user").get(id=doc_id)
            except DoctorProfile.DoesNotExist:
                messages.error(request, "Doctor not found.")
                return redirect("admin_doctors")

            full_name = doc.user.get_full_name() or doc.user.username

            if action == "activate":
                doc.status = "Active"
                doc.save(update_fields=["status"])
                messages.success(request, f"Doctor {full_name} set to Active.")

            elif action == "deactivate":
                doc.status = "Inactive"
                doc.save(update_fields=["status"])
                messages.success(request, f"Doctor {full_name} set to Inactive.")

            elif action == "delete":
                doc.delete()
                messages.success(request, f"Doctor {full_name} deleted.")

        return redirect("admin_doctors")

    # GET: filters
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    doctors = DoctorProfile.objects.select_related("user").all()

    if q:
        doctors = doctors.filter(
            Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(user__email__icontains=q)
            | Q(specialization__icontains=q)
            | Q(hospital__icontains=q)
            | Q(city__icontains=q)
        )

    if status:
        doctors = doctors.filter(status=status)

    doctors = doctors.order_by("user__first_name", "user__last_name")

    return render(
        request,
        "booking/admin_doctors.html",
        {
            "doctors": doctors,
            "q": q,
            "status": status,
            "section": "doctors",
        },
    )


# ============================
# ADMIN: MANAGE PATIENTS
# ============================

@login_required
def admin_patients(request):
    """
    Admin: list and manage patients (non-staff users that are not doctors).
    Actions: Activate / Deactivate / Delete
    """
    if not request.user.is_staff:
        return redirect("home")

    UserModel = get_user_model()
    patients = UserModel.objects.filter(is_staff=False)

    doctor_user_ids = (
        DoctorProfile.objects.values_list("user_id", flat=True).distinct()
    )
    patients = patients.exclude(id__in=doctor_user_ids)

    # POST actions
    if request.method == "POST":
        patient_id = request.POST.get("patient_id")
        action = request.POST.get("action")

        if patient_id and action:
            try:
                p = patients.get(id=patient_id)
            except UserModel.DoesNotExist:
                messages.error(request, "Patient not found.")
                return redirect("admin_patients")

            full_name = p.get_full_name() or p.username

            if action == "activate":
                p.is_active = True
                p.save(update_fields=["is_active"])
                messages.success(request, f"Patient {full_name} set to Active.")
                log_action(request.user, f"Activated patient {full_name} (id={p.id})")

            elif action == "deactivate":
                p.is_active = False
                p.save(update_fields=["is_active"])
                messages.success(request, f"Patient {full_name} set to Inactive.")
                log_action(request.user, f"Deactivated patient {full_name} (id={p.id})")

            elif action == "delete":
                p.delete()
                messages.success(request, f"Patient {full_name} deleted.")
                log_action(request.user, f"Deleted patient {full_name} (id={patient_id})")

        return redirect("admin_patients")

    # GET filters
    q = request.GET.get("q", "").strip()
    if q:
        patients = patients.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(username__icontains=q)
            | Q(email__icontains=q)
        )

    patients = patients.order_by("first_name", "last_name", "username")

    return render(
        request,
        "booking/admin_patients.html",
        {
            "patients": patients,
            "q": q,
            "section": "patients",
        },
    )



# ============================
# ADMIN: APPOINTMENTS + CSV
# ============================

import csv

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.dateparse import parse_date

from .models import Appointment


@login_required
def admin_appointments(request):
    """
    Admin: view all appointments with filters.
    Shows ALL appointments by default (no date limit).
    """
    if not request.user.is_staff:
        return redirect("home")

    # Correct relations: patient (User), doctor (DoctorProfile -> User)
    qs = (
        Appointment.objects
        .select_related("patient", "doctor", "doctor__user")
        .order_by("-date", "-time")
    )

    # --- Filters from GET ---
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    start_date_raw = request.GET.get("start_date", "").strip()
    end_date_raw = request.GET.get("end_date", "").strip()

    # Text search across patient / doctor / hospital / department
    if q:
        qs = qs.filter(
            Q(patient__first_name__icontains=q)
            | Q(patient__last_name__icontains=q)
            | Q(patient__username__icontains=q)
            | Q(patient__email__icontains=q)
            | Q(doctor__user__first_name__icontains=q)
            | Q(doctor__user__last_name__icontains=q)
            | Q(doctor__specialization__icontains=q)
            | Q(hospital__icontains=q)
            | Q(department__icontains=q)
        )

    # Status filter
    if status:
        qs = qs.filter(status=status)

    # Date range filters
    start_date = parse_date(start_date_raw) if start_date_raw else None
    end_date = parse_date(end_date_raw) if end_date_raw else None

    if start_date:
        qs = qs.filter(date__gte=start_date)
    if end_date:
        qs = qs.filter(date__lte=end_date)

    context = {
        "section": "appointments",
        "appointments": qs,
        "q": q,
        "status_filter": status,
        "start_date": start_date_raw,
        "end_date": end_date_raw,
    }
    return render(request, "booking/admin_appointments.html", context)


@login_required
def admin_appointments_export(request):
    """
    Export filtered appointments to CSV.
    Uses the same filters as admin_appointments.
    """
    if not request.user.is_staff:
        return redirect("home")

    appts = (
        Appointment.objects
        .select_related("patient", "doctor", "doctor__user")
        .order_by("-date", "-time")
    )

    # Same query params as template:
    # ?q=&status=&start_date=&end_date=
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    start_date_raw = request.GET.get("start_date", "").strip()
    end_date_raw = request.GET.get("end_date", "").strip()

    if q:
        appts = appts.filter(
            Q(patient__first_name__icontains=q)
            | Q(patient__last_name__icontains=q)
            | Q(patient__username__icontains=q)
            | Q(patient__email__icontains=q)
            | Q(doctor__user__first_name__icontains=q)
            | Q(doctor__user__last_name__icontains=q)
            | Q(doctor__specialization__icontains=q)
            | Q(hospital__icontains=q)
            | Q(department__icontains=q)
        )

    if status:
        appts = appts.filter(status=status)

    start_date = parse_date(start_date_raw) if start_date_raw else None
    end_date = parse_date(end_date_raw) if end_date_raw else None

    if start_date:
        appts = appts.filter(date__gte=start_date)
    if end_date:
        appts = appts.filter(date__lte=end_date)

    # --- Build CSV ---
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="dabs_appointments.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "ID",
            "Appt Code",
            "Patient",
            "Patient Email",
            "Doctor",
            "Specialization",
            "Hospital",
            "Date",
            "Time",
            "Status",
        ]
    )

    for a in appts:
        # Patient details
        patient_user = a.patient
        if patient_user:
            patient_name = patient_user.get_full_name() or patient_user.username
            patient_email = patient_user.email
        else:
            patient_name = ""
            patient_email = ""

        # Doctor details
        doctor_user = a.doctor.user if a.doctor and a.doctor.user else None
        if doctor_user:
            base_name = doctor_user.get_full_name() or doctor_user.username
            doctor_name = f"Dr. {base_name}"
        else:
            doctor_name = ""

        writer.writerow(
            [
                a.id,
                f"A-10{a.id}",  # Appointment code
                patient_name,
                patient_email,
                doctor_name,
                a.doctor.specialization if a.doctor else "",
                a.hospital,
                a.date.isoformat() if a.date else "",
                a.time.strftime("%H:%M") if a.time else "",
                a.status,
            ]
        )

    return response



# ============================
# ADMIN: REPORTS
# ============================

from django.utils import timezone
from django.db.models import Q, Count
from django.utils.dateparse import parse_date

@login_required
def admin_reports(request):
    """
    Admin Reports:
      - Filters: doctor, status, start_date, end_date
      - Summary cards
      - Status table
      - Daily breakdown (SQLite-safe, no TruncDate)
      - Appointment history table (first 100 rows)
    """
    if not request.user.is_staff:
        return redirect("home")

    # ----- read filters from GET -----
    doctor_id = (request.GET.get("doctor") or "").strip()
    status = (request.GET.get("status") or "").strip()
    start_date_str = (request.GET.get("start_date") or "").strip()
    end_date_str = (request.GET.get("end_date") or "").strip()

    # ----- base queryset -----
    qs = (
        Appointment.objects
        .select_related("patient", "patientuser", "doctor", "doctoruser")
        .order_by("-date", "-time")
    )

    if doctor_id:
        qs = qs.filter(doctor_id=doctor_id)
    if status:
        qs = qs.filter(status=status)

    # ----- date filters -----
    start_date = parse_date(start_date_str) if start_date_str else None
    end_date = parse_date(end_date_str) if end_date_str else None

    if start_date:
        qs = qs.filter(date__gte=start_date)
    if end_date:
        qs = qs.filter(date__lte=end_date)

    # ----- summary numbers -----
    total_appointments = qs.count()
    pending_count = qs.filter(status="Pending").count()
    approved_count = qs.filter(status="Approved").count()
    cancelled_count = qs.filter(status="Cancelled").count()

    # ----- status breakdown -----
    status_counts = (
        qs.values("status")
        .annotate(total=Count("id"))
        .order_by()
    )

    # ----- daily overview (max 30 days in result) -----
    daily_counts = (
        qs.filter(date__isnull=False)
        .values("date")
        .annotate(
            total=Count("id"),
            pending=Count("id", filter=Q(status="Pending")),
            approved=Count("id", filter=Q(status="Approved")),
            cancelled=Count("id", filter=Q(status="Cancelled")),
        )
        .order_by("-date")[:30]
    )

    # ----- list of doctors for dropdown -----
    doctors = (
        DoctorProfile.objects
        .select_related("user")
        .order_by("user__first_name", "user__last_name")
    )

    context = {
        "section": "reports",
        "doctors": doctors,
        # used in template to keep selected values
        "doctor_filter": int(doctor_id) if doctor_id else None,
        "status_filter": status,
        "start_date": start_date_str,
        "end_date": end_date_str,

        "total_appointments": total_appointments,
        "pending_count": pending_count,
        "approved_count": approved_count,
        "cancelled_count": cancelled_count,
        "status_counts": status_counts,
        "daily_counts": daily_counts,

        # Appointment History (first 100 rows, but all filters applied)
        "appointments": qs[:100],
    }
    return render(request, "booking/admin_reports.html", context)

# ============================
# ADMIN: SETTINGS
# ============================

@login_required
def admin_settings(request):
    """
    Global system settings stored in single SystemSetting row (pk=1).
    """
    if not request.user.is_staff:
        return redirect("home")

    settings_obj, _ = SystemSetting.objects.get_or_create(pk=1)

    if request.method == "POST":
        site_name = request.POST.get("site_name", "").strip() or "DABS"
        hospital_name = request.POST.get("hospital_name", "").strip()
        support_email = request.POST.get("support_email", "").strip()
        support_phone = request.POST.get("support_phone", "").strip()

        default_slot = request.POST.get("default_slot_minutes", "").strip()
        try:
            default_slot_val = (
                int(default_slot)
                if default_slot
                else settings_obj.default_slot_minutes
            )
            if default_slot_val <= 0:
                default_slot_val = settings_obj.default_slot_minutes or 15
        except ValueError:
            default_slot_val = settings_obj.default_slot_minutes or 15

        settings_obj.site_name = site_name
        settings_obj.hospital_name = hospital_name
        settings_obj.support_email = support_email
        settings_obj.support_phone = support_phone
        settings_obj.default_slot_minutes = default_slot_val

        settings_obj.allow_patient_registration = (
            request.POST.get("allow_patient_registration") == "on"
        )
        settings_obj.allow_doctor_registration = (
            request.POST.get("allow_doctor_registration") == "on"
        )
        settings_obj.maintenance_mode = (
            request.POST.get("maintenance_mode") == "on"
        )

        settings_obj.updated_by = request.user
        settings_obj.save()

        messages.success(request, "Settings updated successfully.")
        return redirect("admin_settings")

    context = {
        "section": "settings",
        "settings_obj": settings_obj,
    }
    return render(request, "booking/admin_settings.html", context)

# ---------------------------
# Admin – System Logs
# ---------------------------

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render

from .models import SystemLog


@login_required
def admin_logs(request):
    """
    Admin: view system logs (user + appointment events).
    Supports simple filters by event type and username.
    """
    if not request.user.is_staff:
        return redirect("home")

    logs = SystemLog.objects.select_related("user")

    event = request.GET.get("event", "").strip()
    user_q = request.GET.get("user", "").strip()

    if event:
        logs = logs.filter(event_type=event)

    if user_q:
        logs = logs.filter(
            Q(user__username__icontains=user_q)
            | Q(user__first_name__icontains=user_q)
            | Q(user__last_name__icontains=user_q)
        )

    # limit to last 300 to avoid huge tables
    logs = logs[:300]

    context = {
        "section": "logs",
        "logs": logs,
        "event": event,
        "user_q": user_q,
    }
    return render(request, "booking/admin_logs.html", context)
