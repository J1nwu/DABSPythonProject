from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.http import HttpResponse
import csv



def login_user(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Invalid username or password.")
            return render(request, "booking/login.html", {"username": username})

        # Log in
        login(request, user)

        # ALWAYS send everyone through the router
        return redirect("route_after_login")

    # GET → show form
    return render(request, "booking/login.html")

# ---------------------------
# Home / Landing page
# ---------------------------
def home(request):
    return render(request, 'booking/home.html')

# ---------------------------
# Patient registration
# ---------------------------
def patient_register(request):
    if request.method == 'POST':
        first = request.POST.get('first_name', '').strip()
        last = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm_password', '')
        # gender = request.POST.get('gender')  # optional for now

        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return redirect('patient_register')

        if not email:
            messages.error(request, "Email is required.")
            return redirect('patient_register')

        username = email  # use email as username

        if User.objects.filter(username=username).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect('patient_register')

        user = User.objects.create_user(username=username, email=email, password=password,
                                        first_name=first, last_name=last)
        user.save()
        messages.success(request, "Registration successful. Please login.")
        return redirect('login')

    return render(request, 'booking/patient_register.html')

# ---------------------------
# Doctor registration
# ---------------------------
def doctor_register(request):
    if request.method == 'POST':
        first = request.POST.get('first_name', '').strip()
        last = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm_password', '')
        regno = request.POST.get('registration_no', '').strip()
        spec = request.POST.get('specialization', '').strip()
        exp = request.POST.get('experience', '0').strip()
        hospital = request.POST.get('hospital', '').strip()
        city = request.POST.get('city', '').strip()
        slot = request.POST.get('slot_pref', '').strip()
        fee = request.POST.get('fee', '').strip()
        bio = request.POST.get('bio', '').strip()

        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return redirect('doctor_register')

        if not email:
            messages.error(request, "Email is required.")
            return redirect('doctor_register')

        username = email  # use email as username

        if User.objects.filter(username=username).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect('doctor_register')

        user = User.objects.create_user(username=username, email=email, password=password,
                                        first_name=first, last_name=last)
        user.save()

        # Fee optional
        fee_value = None
        if fee != '':
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
            status='Pending'
        )

        messages.success(request, "Doctor registered. Status: Pending approval. Please login after approval.")
        return redirect('login')

    return render(request, 'booking/doctor_register.html')

def patient_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'booking/patient_dashboard.html')

# ---------------------------
# Login page (shared)
# ---------------------------


def login_user(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Invalid username or password.")
            return render(request, "booking/login.html", {"username": username})

        # Log the user in
        login(request, user)

        # Always send them through the router
        return redirect("route_after_login")

    # GET request → show form
    return render(request, "booking/login.html")


def logout_user(request):
    logout(request)
    return redirect('login')

from django.contrib.auth.decorators import login_required

@login_required
def patient_dashboard(request):
    return render(request, 'booking/patient_dashboard.html')
from django.db.models import Q


@login_required
def find_doctor(request):
    q = request.GET.get('q', '').strip()
    doctors = DoctorProfile.objects.filter(status='Active')
    if q:
        doctors = doctors.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(specialization__icontains=q) |
            Q(hospital__icontains=q) |
            Q(city__icontains=q)
        )
    return render(request, 'booking/find_doctor.html', {'doctors': doctors, 'q': q})


from datetime import date

@login_required
def book_appointment(request, doctor_id):
    doctor = DoctorProfile.objects.get(id=doctor_id)
    if request.method == 'POST':
        department = request.POST.get('department', '').strip()
        hospital = request.POST.get('hospital', '').strip()
        appt_date = request.POST.get('date', '').strip()
        appt_time = request.POST.get('time', '').strip()
        symptoms = request.POST.get('symptoms', '').strip()

        Appointment.objects.create(
            patient=request.user,
            doctor=doctor,
            department=department,
            hospital=hospital,
            date=appt_date,
            time=appt_time,
            symptoms=symptoms,
            status='Pending'
        )
        messages.success(request, "Appointment booked successfully!")
        return redirect('patient_dashboard')

    return render(request, 'booking/book_appointment.html', {'doctor': doctor, 'today': date.today()})


def doctor_dashboard():
    return None


def post_login_redirect():
    return None
from django.contrib.auth.decorators import login_required


@login_required
def post_login_redirect(request):
    # If user is an active doctor → doctor dashboard, else patient dashboard
    if DoctorProfile.objects.filter(user=request.user, status='Active').exists():
        return redirect('doctor_dashboard')
    return redirect('patient_dashboard')

@login_required
def doctor_dashboard(request):
    doc = DoctorProfile.objects.filter(user=request.user).first()
    # Basic KPIs (safe if no doc profile)
    today_count = Appointment.objects.filter(doctor=doc).count() if doc else 0
    pending_count = Appointment.objects.filter(doctor=doc, status='Pending').count() if doc else 0
    return render(request, 'booking/doctor_dashboard.html', {
        'doc': doc,
        'today_count': today_count,
        'pending_count': pending_count,
    })


from django.contrib.auth.decorators import login_required
from .models import DoctorProfile

@login_required
def route_after_login(request):
    user = request.user

    # 1) Admin / staff → Admin UI
    if user.is_superuser or user.is_staff:
        return redirect("admin_dashboard")

    # 2) Doctor → Doctor dashboard
    #    (any user that has a DoctorProfile is treated as doctor)
    if DoctorProfile.objects.filter(user=user).exists():
        return redirect("doctor_dashboard")

    # 3) Everyone else → Patient dashboard
    return redirect("patient_dashboard")


from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

@login_required
def my_appointments(request):
    appts = Appointment.objects.filter(patient=request.user).order_by('-date', '-time')
    return render(request, 'booking/my_appointments.html', {'appts': appts})


from django.utils.dateparse import parse_date


@login_required
def cancel_appointment(request, appt_id):
    try:
        appt = Appointment.objects.get(id=appt_id, patient=request.user)
    except Appointment.DoesNotExist:
        raise Http404("Appointment not found")

    if request.method != 'POST':
        return redirect('my_appointments')

    if appt.status in ['Completed', 'Cancelled']:
        messages.error(request, "This appointment cannot be cancelled.")
        return redirect('my_appointments')

    appt.status = 'Cancelled'
    appt.save()
    messages.success(request, "Appointment cancelled.")
    return redirect('my_appointments')


@login_required
def reschedule_appointment(request, appt_id):
    try:
        appt = Appointment.objects.get(id=appt_id, patient=request.user)
    except Appointment.DoesNotExist:
        raise Http404("Appointment not found")

    if request.method == 'GET':
        # show reschedule form
        return render(request, 'booking/reschedule_appointment.html', {'appt': appt})

    # POST: apply new date/time
    new_date_str = request.POST.get('date', '').strip()
    new_time_str = request.POST.get('time', '').strip()

    if not new_date_str or not new_time_str:
        messages.error(request, "Both date and time are required.")
        return redirect('reschedule_appointment', appt_id=appt.id)

    try:
        new_date = parse_date(new_date_str)
        new_time = datetime.strptime(new_time_str, '%H:%M').time()
    except Exception:
        messages.error(request, "Invalid date or time.")
        return redirect('reschedule_appointment', appt_id=appt.id)

    if appt.status == 'Cancelled' or appt.status == 'Completed':
        messages.error(request, "This appointment cannot be rescheduled.")
        return redirect('my_appointments')

    appt.date = new_date
    appt.time = new_time
    appt.status = 'Rescheduled'
    appt.save()
    messages.success(request, "Appointment rescheduled.")
    return redirect('my_appointments')
@login_required
def doctor_approvals(request):
    try:
        doctor = DoctorProfile.objects.get(user=request.user)
    except DoctorProfile.DoesNotExist:
        return redirect('patient_dashboard')

    appts = Appointment.objects.filter(doctor=doctor, status='Pending').order_by('date', 'time')
    return render(request, 'booking/doctor_approvals.html', {'appts': appts})


@login_required
def doctor_approve(request, appt_id):
    try:
        appt = Appointment.objects.get(id=appt_id, doctor__user=request.user)
    except Appointment.DoesNotExist:
        raise Http404("Appointment not found")

    appt.status = 'Approved'
    appt.save()
    messages.success(request, "Appointment Approved.")
    return redirect('doctor_approvals')


@login_required
def doctor_reject(request, appt_id):
    try:
        appt = Appointment.objects.get(id=appt_id, doctor__user=request.user)
    except Appointment.DoesNotExist:
        raise Http404("Appointment not found")

    appt.status = 'Rejected'
    appt.save()
    messages.success(request, "Appointment Rejected.")
    return redirect('doctor_approvals')


@login_required
def doctor_reschedule(request, appt_id):
    try:
        appt = Appointment.objects.get(id=appt_id, doctor__user=request.user)
    except Appointment.DoesNotExist:
        raise Http404("Appointment not found")

    if request.method == 'GET':
        return render(request, 'booking/doctor_reschedule.html', {'appt': appt})

    new_date = request.POST.get('date')
    new_time = request.POST.get('time')

    if not new_date or not new_time:
        messages.error(request, "Both date and time are required.")
        return redirect('doctor_reschedule', appt_id=appt.id)

    appt.date = new_date
    appt.time = new_time
    appt.status = 'Rescheduled'
    appt.save()

    messages.success(request, "Appointment Rescheduled.")
    return redirect('doctor_approvals')
from django.http import HttpResponseRedirect
from django.urls import reverse


@login_required
def cancel_appointment(request, pk):
    appt = get_object_or_404(Appointment, pk=pk, patient=request.user)
    if request.method != "POST":
        return HttpResponseForbidden("POST required")
    # Optional: prevent cancelling past appointments
    if appt.datetime and appt.datetime < timezone.now():
        messages.error(request, "Past appointments cannot be cancelled.")
        return HttpResponseRedirect(reverse('my_appointments'))
    appt.status = "Cancelled"
    appt.save(update_fields=["status"])
    messages.success(request, f"Appointment #{appt.id} cancelled.")
    return HttpResponseRedirect(reverse('my_appointments'))


from django.http import HttpResponseForbidden
from django.contrib import messages
from django.utils import timezone
from datetime import datetime


@login_required
def cancel_appointment(request, appt_id):
    # POST-only; only the owner (patient) can cancel
    if request.method != 'POST':
        return HttpResponseForbidden("POST required")

    appt = get_object_or_404(Appointment, id=appt_id, patient=request.user)

    # Optional: block cancelling completed/cancelled
    if appt.status in ['Completed', 'Cancelled']:
        messages.error(request, "This appointment cannot be cancelled.")
        return redirect('my_appointments')

    # Optional: block cancelling past datetime
    try:
        appt_dt = datetime.combine(appt.date, appt.time)
        appt_dt = timezone.make_aware(appt_dt) if timezone.is_naive(appt_dt) else appt_dt
        if appt_dt <= timezone.now():
            messages.error(request, "Past appointments cannot be cancelled.")
            return redirect('my_appointments')
    except Exception:
        pass

    appt.status = 'Cancelled'
    appt.save(update_fields=['status'])
    messages.success(request, "Appointment cancelled.")
    return redirect('my_appointments')


@login_required
def reschedule_appointment(request, appt_id):
    appt = get_object_or_404(Appointment, id=appt_id, patient=request.user)

    if request.method == 'GET':
        # Show reschedule form
        return render(request, 'booking/reschedule_appointment.html', {'appt': appt})

    # POST: apply new date/time
    new_date_str = request.POST.get('date', '').strip()
    new_time_str = request.POST.get('time', '').strip()

    if not new_date_str or not new_time_str:
        messages.error(request, "Both date and time are required.")
        return redirect('reschedule_appointment', appt_id=appt.id)

    # Parse values
    try:
        new_date = datetime.strptime(new_date_str, '%Y-%m-%d').date()
        new_time = datetime.strptime(new_time_str, '%H:%M').time()
    except ValueError:
        messages.error(request, "Invalid date or time.")
        return redirect('reschedule_appointment', appt_id=appt.id)

    # Must be future
    new_dt = datetime.combine(new_date, new_time)
    new_dt = timezone.make_aware(new_dt) if timezone.is_naive(new_dt) else new_dt
    if new_dt <= timezone.now():
        messages.error(request, "Choose a future date/time.")
        return redirect('reschedule_appointment', appt_id=appt.id)

    # Update — set status to Rescheduled (or Pending, your choice)
    appt.date = new_date
    appt.time = new_time
    appt.status = 'Rescheduled'
    appt.save(update_fields=['date', 'time', 'status'])

    messages.success(request, "Appointment rescheduled.")
    return redirect('my_appointments')


@login_required
def doctor_approvals(request):
    try:
        doctor = DoctorProfile.objects.get(user=request.user)
    except DoctorProfile.DoesNotExist:
        return redirect('patient_dashboard')
    appts = Appointment.objects.filter(doctor=doctor, status='Pending').order_by('date', 'time')
    return render(request, 'booking/doctor_approvals.html', {'appts': appts})

@login_required
def doctor_approve(request, appt_id):
    try:
        appt = Appointment.objects.get(id=appt_id, doctor__user=request.user)
    except Appointment.DoesNotExist:
        raise Http404("Appointment not found")
    appt.status = 'Approved'
    appt.save(update_fields=['status'])
    messages.success(request, "Appointment Approved.")
    return redirect('doctor_approvals')

@login_required
def doctor_reject(request, appt_id):
    try:
        appt = Appointment.objects.get(id=appt_id, doctor__user=request.user)
    except Appointment.DoesNotExist:
        raise Http404("Appointment not found")
    appt.status = 'Rejected'
    appt.save(update_fields=['status'])
    messages.success(request, "Appointment Rejected.")
    return redirect('doctor_approvals')

@login_required
def doctor_reschedule(request, appt_id):
    try:
        appt = Appointment.objects.get(id=appt_id, doctor__user=request.user)
    except Appointment.DoesNotExist:
        raise Http404("Appointment not found")

    if request.method == 'GET':
        return render(request, 'booking/doctor_reschedule.html', {'appt': appt})

    new_date = request.POST.get('date', '').strip()
    new_time = request.POST.get('time', '').strip()
    if not new_date or not new_time:
        messages.error(request, "Both date and time are required.")
        return redirect('doctor_reschedule', appt_id=appt.id)

    from datetime import datetime
    try:
        nd = datetime.strptime(new_date, '%Y-%m-%d').date()
        nt = datetime.strptime(new_time, '%H:%M').time()
    except ValueError:
        messages.error(request, "Invalid date/time.")
        return redirect('doctor_reschedule', appt_id=appt.id)

    appt.date = nd
    appt.time = nt
    appt.status = 'Rescheduled'
    appt.save(update_fields=['date', 'time', 'status'])
    messages.success(request, "Appointment Rescheduled.")
    return redirect('doctor_approvals')
@login_required
def doctor_dashboard(request):
    from django.shortcuts import get_object_or_404
    profile = get_object_or_404(DoctorProfile, user=request.user)
    return render(request, 'booking/doctor_dashboard.html', {'profile': profile})


def approve_appt():
    return None


def reject_appt():
    return None
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Appointment

from django.http import Http404

@login_required
def doctor_approvals(request):
    try:
        doctor = DoctorProfile.objects.get(user=request.user)
    except DoctorProfile.DoesNotExist:
        return redirect('patient_dashboard')

    appts = Appointment.objects.filter(doctor=doctor, status='Pending').order_by('date', 'time')
    return render(request, 'booking/doctor_approvals.html', {'appts': appts})


@login_required
def doctor_approve(request, appt_id):
    try:
        appt = Appointment.objects.get(id=appt_id, doctor__user=request.user)
    except Appointment.DoesNotExist:
        raise Http404("Appointment not found")

    appt.status = 'Approved'
    appt.save(update_fields=['status'])
    messages.success(request, "Appointment Approved.")
    return redirect('doctor_approvals')


@login_required
def doctor_reject(request, appt_id):
    try:
        appt = Appointment.objects.get(id=appt_id, doctor__user=request.user)
    except Appointment.DoesNotExist:
        raise Http404("Appointment not found")

    appt.status = 'Rejected'
    appt.save(update_fields=['status'])
    messages.success(request, "Appointment Rejected.")
    return redirect('doctor_approvals')


@login_required
def doctor_reschedule(request, appt_id):
    try:
        appt = Appointment.objects.get(id=appt_id, doctor__user=request.user)
    except Appointment.DoesNotExist:
        raise Http404("Appointment not found")

    if request.method == 'GET':
        return render(request, 'booking/doctor_reschedule.html', {'appt': appt})

    new_date = request.POST.get('date', '').strip()
    new_time = request.POST.get('time', '').strip()
    if not new_date or not new_time:
        messages.error(request, "Both date and time are required.")
        return redirect('doctor_reschedule', appt_id=appt.id)

    from datetime import datetime
    try:
        nd = datetime.strptime(new_date, '%Y-%m-%d').date()
        nt = datetime.strptime(new_time, '%H:%M').time()
    except ValueError:
        messages.error(request, "Invalid date/time.")
        return redirect('doctor_reschedule', appt_id=appt.id)

    appt.date = nd
    appt.time = nt
    appt.status = 'Rescheduled'
    appt.save(update_fields=['date', 'time', 'status'])
    messages.success(request, "Appointment Rescheduled.")
    return redirect('doctor_approvals')
@login_required
def doctor_schedule(request):
    try:
        profile = DoctorProfile.objects.get(user=request.user)
    except DoctorProfile.DoesNotExist:
        return redirect('patient_dashboard')

    if request.method == 'POST':
        working_days = request.POST.get('working_days', '').strip()
        start = request.POST.get('clinic_start_time', '').strip()
        end = request.POST.get('clinic_end_time', '').strip()
        bstart = request.POST.get('break_start_time', '').strip()
        bend = request.POST.get('break_end_time', '').strip()
        slot = request.POST.get('slot_minutes', '').strip()
        notes = request.POST.get('schedule_notes', '').strip()
        published = request.POST.get('schedule_published') == 'on'

        def parse_time(value):
            if not value:
                return None
            try:
                return datetime.strptime(value, "%H:%M").time()
            except ValueError:
                return None

        profile.working_days = working_days
        profile.clinic_start_time = parse_time(start)
        profile.clinic_end_time = parse_time(end)
        profile.break_start_time = parse_time(bstart)
        profile.break_end_time = parse_time(bend)
        profile.slot_minutes = int(slot) if slot.isdigit() else None
        profile.schedule_notes = notes
        profile.schedule_published = published
        profile.save()

        messages.success(request, "Schedule updated.")
        return redirect('doctor_schedule')

    # GET
    return render(request, 'booking/doctor_schedule.html', {'profile': profile})


def doctor_appointments():
    return None
@login_required
def doctor_appointments(request):
    """
    Show this doctor's appointments (today + upcoming) with ability to
    quickly mark them as Completed or Cancelled.
    """
    try:
        doctor = DoctorProfile.objects.get(user=request.user)
    except DoctorProfile.DoesNotExist:
        return redirect('patient_dashboard')

    # Simple filter: today and future appointments
    from django.utils import timezone
    today = timezone.localdate()
    appts = Appointment.objects.filter(
        doctor=doctor,
        date__gte=today
    ).order_by('date', 'time')

    # If doctor clicked a status action
    if request.method == 'POST':
        appt_id = request.POST.get('appt_id')
        action = request.POST.get('action')  # 'complete' or 'cancel'
        if appt_id and action:
            try:
                appt = Appointment.objects.get(id=appt_id, doctor=doctor)
                if action == 'complete':
                    appt.status = 'Completed'
                elif action == 'cancel':
                    appt.status = 'Cancelled'
                appt.save(update_fields=['status'])
                messages.success(request, "Appointment status updated.")
            except Appointment.DoesNotExist:
                messages.error(request, "Appointment not found.")
        return redirect('doctor_appointments')

    return render(request, 'booking/doctor_appointments.html', {'appts': appts})
@login_required
def doctor_patients(request):
    """
    List distinct patients who have at least one appointment with this doctor.
    """
    try:
        doctor = DoctorProfile.objects.get(user=request.user)
    except DoctorProfile.DoesNotExist:
        return redirect('patient_dashboard')

    from django.contrib.auth import get_user_model
    User = get_user_model()

    # Get unique patient IDs from this doctor's appointments
    patient_ids = (
        Appointment.objects
        .filter(doctor=doctor)
        .values_list('patient_id', flat=True)
        .distinct()
    )

    patients = User.objects.filter(id__in=patient_ids).order_by('first_name', 'last_name')

    return render(request, 'booking/doctor_patients.html', {'patients': patients})
@login_required
def admin_dashboard(request):
    # Only admin users can access
    if not request.user.is_staff:
        return redirect('home')

    from django.contrib.auth import get_user_model
    User = get_user_model()

    total_doctors = DoctorProfile.objects.filter(status='Approved').count()
    pending_doctors = DoctorProfile.objects.filter(status='Pending').count()
    total_patients = User.objects.filter(is_staff=False).count()

    from django.utils import timezone
    today = timezone.localdate()
    todays_appointments = Appointment.objects.filter(date=today).count()

    context = {
        "total_doctors": total_doctors,
        "pending_doctors": pending_doctors,
        "total_patients": total_patients,
        "todays_appointments": todays_appointments,
    }

    return render(request, 'booking/admin_dashboard.html', context)
@login_required
def admin_pending_doctors(request):
    # Only staff/admin users can access
    if not request.user.is_staff:
        return redirect('home')

    # Handle approve / reject actions
    if request.method == 'POST':
        doctor_id = request.POST.get('doctor_id')
        action = request.POST.get('action')  # 'approve' or 'reject'
        note = request.POST.get('review_note', '').strip()

        from django.utils import timezone

        if doctor_id and action:
            try:
                doc = DoctorProfile.objects.get(id=doctor_id, status='Pending')
                if action == 'approve':
                    doc.status = 'Approved'
                    messages.success(request, f"Doctor {doc.user.get_full_name()} approved.")
                elif action == 'reject':
                    doc.status = 'Rejected'
                    if note:
                        doc.review_note = note
                    messages.success(request, f"Doctor {doc.user.get_full_name()} rejected.")
                # Common fields
                doc.reviewed_by = request.user
                doc.reviewed_at = timezone.now()
                doc.save()
            except DoctorProfile.DoesNotExist:
                messages.error(request, "Doctor application not found or no longer pending.")

        return redirect('admin_pending_doctors')

    # GET request: show all pending doctor profiles
    pending = DoctorProfile.objects.filter(status='Pending').select_related('user').order_by('user__first_name')

    return render(request, 'booking/admin_pending_doctors.html', {'pending': pending})
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

@login_required
def route_after_login(request):
    user = request.user

    # 1) Admin (staff or superuser) → Admin UI dashboard
    if user.is_staff or user.is_superuser:
        return redirect('admin_dashboard')

    # 2) Doctor → Doctor dashboard (any user linked to a DoctorProfile)
    if DoctorProfile.objects.filter(user=user).exists():
        return redirect('doctor_dashboard')

    # 3) Everyone else → Patient dashboard
    return redirect('patient_dashboard')
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from .models import DoctorProfile, Appointment

# ---------- Admin: Doctor Applications (Pending only) ----------

@login_required
def admin_doctor_applications(request):
    if not request.user.is_staff and not request.user.is_superuser:
        return redirect('home')

    pending_doctors = (
        DoctorProfile.objects
        .filter(status='Pending')
        .select_related('user')
        .order_by('user__first_name', 'user__last_name')
    )

    context = {
        "pending_doctors": pending_doctors,
    }
    return render(request, 'booking/admin_doctor_applications.html', context)


# ---------- Admin: All Doctors list ----------

@login_required
def admin_doctors(request):
    if not request.user.is_staff and not request.user.is_superuser:
        return redirect('home')

    doctors = (
        DoctorProfile.objects
        .select_related('user')
        .order_by('user__first_name', 'user__last_name')
    )

    context = {
        "doctors": doctors,
    }
    return render(request, 'booking/admin_doctors.html', context)


# ---------- Admin: Patients list ----------

@login_required
def admin_patients(request):
    if not request.user.is_staff and not request.user.is_superuser:
        return redirect('home')

    User = get_user_model()

    patients = (
        User.objects
        .filter(is_staff=False, is_superuser=False)
        .order_by('first_name', 'last_name')
    )

    context = {
        "patients": patients,
    }
    return render(request, 'booking/admin_patients.html', context)
# ============================
# ADMIN LIST PAGES
# ============================

@login_required
def admin_doctors(request):
    if not request.user.is_staff:
        return redirect('home')

    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    doctors = DoctorProfile.objects.select_related('user').all()

    if status:
        doctors = doctors.filter(status=status)

    if q:
        doctors = doctors.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__email__icontains=q) |
            Q(specialization__icontains=q) |
            Q(hospital__icontains=q)
        )

    doctors = doctors.order_by('user__first_name', 'user__last_name')

    return render(request, 'booking/admin_doctors.html', {
        'doctors': doctors,
        'q': q,
        'status': status,
        'section': 'doctors',
    })


@login_required
def admin_patients(request):
    if not request.user.is_staff:
        return redirect('home')

    from django.contrib.auth import get_user_model
    UserModel = get_user_model()

    q = request.GET.get('q', '').strip()

    # Non-staff, non-doctor users → treat as patients
    doctor_user_ids = DoctorProfile.objects.values_list('user_id', flat=True)
    patients = UserModel.objects.filter(is_staff=False).exclude(id__in=doctor_user_ids)

    if q:
        patients = patients.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(username__icontains=q) |
            Q(email__icontains=q)
        )

    patients = patients.order_by('first_name', 'last_name')

    return render(request, 'booking/admin_patients.html', {
        'patients': patients,
        'q': q,
        'section': 'patients',
    })


@login_required
def admin_appointments(request):
    if not request.user.is_staff:
        return redirect('home')

    # Filters
    doctor_id = request.GET.get('doctor', '').strip()
    status = request.GET.get('status', '').strip()
    start = request.GET.get('start', '').strip()
    end = request.GET.get('end', '').strip()

    appts = Appointment.objects.select_related('doctor__user', 'patient').all()

    if doctor_id:
        appts = appts.filter(doctor_id=doctor_id)

    if status:
        appts = appts.filter(status=status)

    if start:
        appts = appts.filter(date__gte=start)
    if end:
        appts = appts.filter(date__lte=end)

    appts = appts.order_by('-date', '-time')

    doctors = DoctorProfile.objects.filter(status__in=['Active', 'Approved']).select_related('user')

    return render(request, 'booking/admin_appointments.html', {
        'appts': appts,
        'doctors': doctors,
        'chosen_doctor': doctor_id,
        'chosen_status': status,
        'start': start,
        'end': end,
        'section': 'appointments',
    })


@login_required
def admin_export_appointments_csv(request):
    if not request.user.is_staff:
        return redirect('home')

    # Use same filtering as admin_appointments (simple version)
    doctor_id = request.GET.get('doctor', '').strip()
    status = request.GET.get('status', '').strip()
    start = request.GET.get('start', '').strip()
    end = request.GET.get('end', '').strip()

    appts = Appointment.objects.select_related('doctor__user', 'patient').all()
    if doctor_id:
        appts = appts.filter(doctor_id=doctor_id)
    if status:
        appts = appts.filter(status=status)
    if start:
        appts = appts.filter(date__gte=start)
    if end:
        appts = appts.filter(date__lte=end)

    # CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="appointments.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Patient', 'Doctor', 'Department', 'Hospital',
                     'Date', 'Time', 'Status'])

    for a in appts:
        writer.writerow([
            a.id,
            a.patient.get_full_name() or a.patient.username,
            f"Dr. {a.doctor.user.get_full_name()}",
            a.department,
            a.hospital,
            a.date,
            a.time,
            a.status,
        ])
    return response


@login_required
def admin_reports(request):
    if not request.user.is_staff:
        return redirect('home')

    # Simple status counts for chart / summary
    counts = (
        Appointment.objects
        .values('status')
        .annotate(total=Count('id'))
    )
    # Turn into dict: {'Pending': 10, 'Approved': 5, ...}
    status_map = {c['status']: c['total'] for c in counts}
    labels = ['Pending', 'Approved', 'Rescheduled', 'Cancelled', 'Completed']
    data = [status_map.get(label, 0) for label in labels]

    return render(request, 'booking/admin_reports.html', {
        'labels': labels,
        'data': data,
        'section': 'reports',
    })


@login_required
def admin_settings(request):
    if not request.user.is_staff:
        return redirect('home')

    # For now just a placeholder page
    return render(request, 'booking/admin_settings.html', {
        'section': 'settings',
    })
@login_required
def admin_dashboard(request):
    # Only admin users can access
    if not request.user.is_staff:
        return redirect('home')

    from django.contrib.auth import get_user_model
    User = get_user_model()

    total_doctors = DoctorProfile.objects.filter(status='Approved').count()
    pending_doctors = DoctorProfile.objects.filter(status='Pending').count()
    total_patients = User.objects.filter(is_staff=False).count()

    from django.utils import timezone
    today = timezone.localdate()
    todays_appointments = Appointment.objects.filter(date=today).count()

    context = {
        "total_doctors": total_doctors,
        "pending_doctors": pending_doctors,
        "total_patients": total_patients,
        "todays_appointments": todays_appointments,
        "section": "dashboard",   # <-- needed for sidebar highlight
    }

    return render(request, 'booking/admin_dashboard.html', context)
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages

@login_required
def admin_pending_doctors(request):
    # Only staff/admin users can access
    if not request.user.is_staff:
        return redirect('home')

    # Handle approve / reject
    if request.method == 'POST':
        doctor_id = request.POST.get('doctor_id')
        action = request.POST.get('action')  # 'approve' or 'reject'

        if not doctor_id or action not in ['approve', 'reject']:
            messages.error(request, "Invalid action.")
            return redirect('admin_pending_doctors')

        doc = get_object_or_404(DoctorProfile, id=doctor_id, status='Pending')

        if action == 'approve':
            doc.status = 'Active'      # use existing choice
            messages.success(request, f"Doctor {doc.user.get_full_name()} approved.")
        elif action == 'reject':
            doc.status = 'Inactive'    # treat rejected as inactive
            messages.success(request, f"Doctor {doc.user.get_full_name()} rejected.")

        doc.save(update_fields=['status'])
        return redirect('admin_pending_doctors')

    # GET → show all pending
    pending = (
        DoctorProfile.objects
        .filter(status='Pending')
        .select_related('user')
        .order_by('user__first_name')
    )

    context = {
        'pending': pending,
        'section': 'applications',   # highlight sidebar item
    }
    return render(request, 'booking/admin_pending_doctors.html', context)

from django.contrib import messages
from django.contrib.auth.models import User
from .models import DoctorProfile

def doctor_register(request):
    if request.method == 'POST':
        first = request.POST.get('first_name', '').strip()
        last = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm_password', '')
        regno = request.POST.get('registration_no', '').strip()
        spec = request.POST.get('specialization', '').strip()
        exp = request.POST.get('experience', '0').strip()
        hospital = request.POST.get('hospital', '').strip()
        city = request.POST.get('city', '').strip()
        slot = request.POST.get('slot_pref', '').strip()
        fee = request.POST.get('fee', '').strip()
        bio = request.POST.get('bio', '').strip()

        # Basic validations
        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return redirect('doctor_register')

        if not email:
            messages.error(request, "Email is required.")
            return redirect('doctor_register')

        username = email  # we use email as username

        if User.objects.filter(username=username).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect('doctor_register')

        # 1) Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first,
            last_name=last
        )

        # 2) Parse optional fee
        fee_value = None
        if fee:
            try:
                fee_value = float(fee)
            except ValueError:
                fee_value = None

        # 3) Create DoctorProfile with status = Pending
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
            status='Pending',  # 🔴 KEY: must be exactly this
        )

        messages.success(
            request,
            "Doctor registered. Status: Pending approval. You can login after admin approval."
        )
        return redirect('login')

    # GET
    return render(request, 'booking/doctor_register.html')
# ===========================
# ADMIN: MANAGE DOCTORS
# ===========================
@login_required
def admin_doctors(request):
    if not request.user.is_staff:
        return redirect('home')

    # Handle activate / deactivate actions
    if request.method == "POST":
        doc_id = request.POST.get("doctor_id")
        action = request.POST.get("action")     # activate / deactivate

        try:
            doctor = DoctorProfile.objects.get(id=doc_id)
            if action == "activate":
                doctor.status = "Active"
            elif action == "deactivate":
                doctor.status = "Inactive"
            doctor.save()
            messages.success(request, f"Doctor {doctor.user.get_full_name()} updated.")
        except DoctorProfile.DoesNotExist:
            messages.error(request, "Doctor not found.")

        return redirect("admin_doctors")

    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    doctors = DoctorProfile.objects.select_related("user")

    if status:
        doctors = doctors.filter(status=status)

    if q:
        doctors = doctors.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__email__icontains=q) |
            Q(specialization__icontains=q) |
            Q(hospital__icontains=q)
        )

    doctors = doctors.order_by('user__first_name', 'user__last_name')

    return render(request, "booking/admin_doctors.html", {
        "doctors": doctors,
        "section": "doctors",
        "q": q,
        "status": status,
    })
# ===========================
# ADMIN: MANAGE DOCTORS LIST
# ===========================
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from .models import DoctorProfile

@login_required
def admin_doctors(request):
    # Only staff/admin users can access this page
    if not request.user.is_staff:
        return redirect('home')

    # Read filters from GET
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    # Base queryset
    doctors = DoctorProfile.objects.select_related('user').all()

    # Text search (name, email, specialization, hospital, city)
    if q:
        doctors = doctors.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__email__icontains=q) |
            Q(specialization__icontains=q) |
            Q(hospital__icontains=q) |
            Q(city__icontains=q)
        )

    # Status filter (Pending / Active / Inactive)
    if status:
        doctors = doctors.filter(status=status)

    doctors = doctors.order_by('user__first_name', 'user__last_name')

    return render(request, 'booking/admin_doctors.html', {
        'doctors': doctors,
        'q': q,
        'status': status,
        'section': 'doctors',   # for sidebar highlight
    })
# ===========================
# ADMIN: MANAGE DOCTORS (LIST + ACTIONS)
# ===========================
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from .models import DoctorProfile

@login_required
def admin_doctors(request):
    # Only staff/admin users can access this page
    if not request.user.is_staff:
        return redirect('home')

    # --------- POST: actions (Activate / Deactivate / Delete) ----------
    if request.method == 'POST':
        doc_id = request.POST.get('doctor_id')
        action = request.POST.get('action')

        if doc_id and action:
            try:
                doc = DoctorProfile.objects.select_related('user').get(id=doc_id)
            except DoctorProfile.DoesNotExist:
                messages.error(request, "Doctor not found.")
                return redirect('admin_doctors')

            full_name = doc.user.get_full_name() or doc.user.username

            if action == 'activate':
                doc.status = 'Active'
                doc.save(update_fields=['status'])
                messages.success(request, f"Doctor {full_name} set to Active.")

            elif action == 'deactivate':
                doc.status = 'Inactive'
                doc.save(update_fields=['status'])
                messages.success(request, f"Doctor {full_name} set to Inactive.")

            elif action == 'delete':
                doc.delete()
                messages.success(request, f"Doctor {full_name} deleted.")

        return redirect('admin_doctors')

    # --------- GET: list + filters ----------
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()

    doctors = DoctorProfile.objects.select_related('user').all()

    # Text search
    if q:
        doctors = doctors.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__email__icontains=q) |
            Q(specialization__icontains=q) |
            Q(hospital__icontains=q) |
            Q(city__icontains=q)
        )

    # Status filter (handles Pending / Active / Inactive / Approved / Rejected)
    if status:
        doctors = doctors.filter(status=status)

    doctors = doctors.order_by('user__first_name', 'user__last_name')

    return render(request, 'booking/admin_doctors.html', {
        'doctors': doctors,
        'q': q,
        'status': status,
        'section': 'doctors',   # sidebar highlight
    })
# ===========================
# ADMIN: MANAGE PATIENTS
# ===========================
from django.contrib.auth import get_user_model
from django.db.models import Q

@login_required
def admin_patients(request):
    # Only staff/admin users can access
    if not request.user.is_staff:
        return redirect('home')

    User = get_user_model()

    # Base queryset: non-staff normal users
    patients = User.objects.filter(is_staff=False)

    # Exclude doctor accounts (users having a DoctorProfile)
    doctor_user_ids = DoctorProfile.objects.values_list('user_id', flat=True).distinct()
    patients = patients.exclude(id__in=doctor_user_ids)

    # ---------- POST: actions (activate / deactivate / delete) ----------
    if request.method == "POST":
        patient_id = request.POST.get("patient_id")
        action = request.POST.get("action")

        if patient_id and action:
            try:
                p = patients.get(id=patient_id)
            except User.DoesNotExist:
                messages.error(request, "Patient not found.")
                return redirect("admin_patients")

            full_name = p.get_full_name() or p.username

            if action == "activate":
                p.is_active = True
                p.save(update_fields=["is_active"])
                messages.success(request, f"Patient {full_name} set to Active.")

            elif action == "deactivate":
                p.is_active = False
                p.save(update_fields=["is_active"])
                messages.success(request, f"Patient {full_name} set to Inactive.")

            elif action == "delete":
                p.delete()
                messages.success(request, f"Patient {full_name} deleted.")

        return redirect("admin_patients")

    # ---------- GET: filters ----------
    q = request.GET.get("q", "").strip()

    if q:
        patients = patients.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(username__icontains=q)
            | Q(email__icontains=q)
        )

    patients = patients.order_by("first_name", "last_name", "username")

    return render(request, "booking/admin_patients.html", {
        "patients": patients,
        "q": q,
        "section": "patients",   # to highlight sidebar
    })
# ===========================
# ADMIN: ALL APPOINTMENTS + CSV EXPORT
# ===========================
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils.dateparse import parse_date
from django.db.models import Q
from django.http import HttpResponse
import csv

@login_required
def admin_appointments(request):
    # Only staff/admin users can access
    if not request.user.is_staff:
        return redirect('home')

    # Base queryset
    appts = Appointment.objects.select_related('patient', 'doctor__user').all()

    # ---- Filters from query string ----
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    date_from = request.GET.get("from", "").strip()
    date_to = request.GET.get("to", "").strip()

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

    if date_from:
        df = parse_date(date_from)
        if df:
            appts = appts.filter(date__gte=df)

    if date_to:
        dt = parse_date(date_to)
        if dt:
            appts = appts.filter(date__lte=dt)

    appts = appts.order_by('-date', '-time')

    return render(request, "booking/admin_appointments.html", {
        "appts": appts,
        "q": q,
        "status": status,
        "date_from": date_from,
        "date_to": date_to,
        "section": "appointments",
    })


@login_required
def admin_export_appointments_csv(request):
    # Only staff/admin users can access
    if not request.user.is_staff:
        return redirect('home')

    appts = Appointment.objects.select_related('patient', 'doctor__user').all()

    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    date_from = request.GET.get("from", "").strip()
    date_to = request.GET.get("to", "").strip()

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

    if date_from:
        df = parse_date(date_from)
        if df:
            appts = appts.filter(date__gte=df)

    if date_to:
        dt = parse_date(date_to)
        if dt:
            appts = appts.filter(date__lte=dt)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="dabs_appointments.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "ID",
        "Appt Code",
        "Patient",
        "Patient Email",
        "Doctor",
        "Specialization",
        "Department",
        "Hospital",
        "Date",
        "Time",
        "Status",
    ])

    for a in appts.order_by('-date', '-time'):
        patient_name = a.patient.get_full_name() or a.patient.username
        doctor_name = f"Dr. {a.doctor.user.get_full_name()}" if a.doctor and a.doctor.user else ""
        writer.writerow([
            a.id,
            f"A-10{a.id}",
            patient_name,
            a.patient.email,
            doctor_name,
            a.doctor.specialization if a.doctor else "",
            a.department,
            a.hospital,
            a.date.isoformat() if a.date else "",
            a.time.strftime("%H:%M") if a.time else "",
            a.status,
        ])

    return response
