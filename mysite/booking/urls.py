# booking/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Home & auth
    path('', views.home, name='home'),
    path('register/patient/', views.patient_register, name='patient_register'),
    path('register/doctor/', views.doctor_register, name='doctor_register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),

    # Routing after login
    path('route/', views.route_after_login, name='route_after_login'),
    path('post-login/', views.post_login_redirect, name='post_login_redirect'),

    # Patient area
    path('dashboard/patient/', views.patient_dashboard, name='patient_dashboard'),
    path('dashboard/patient/find/', views.find_doctor, name='find_doctor'),
    path('dashboard/patient/book/<int:doctor_id>/', views.book_appointment, name='book_appointment'),
    path('dashboard/patient/appointments/', views.my_appointments, name='my_appointments'),
    path('dashboard/patient/appointments/<int:appt_id>/cancel/', views.cancel_appointment, name='cancel_appointment'),
    path('dashboard/patient/appointments/<int:appt_id>/reschedule/', views.reschedule_appointment, name='reschedule_appointment'),

    # Doctor area
    path('dashboard/doctor/', views.doctor_dashboard, name='doctor_dashboard'),
    path('dashboard/doctor/approvals/', views.doctor_approvals, name='doctor_approvals'),
    path('dashboard/doctor/approvals/<int:appt_id>/approve/', views.doctor_approve, name='doctor_approve'),
    path('dashboard/doctor/approvals/<int:appt_id>/reject/', views.doctor_reject, name='doctor_reject'),
    path('dashboard/doctor/approvals/<int:appt_id>/reschedule/', views.doctor_reschedule, name='doctor_reschedule'),
    path('dashboard/doctor/schedule/', views.doctor_schedule, name='doctor_schedule'),
    path('dashboard/doctor/appointments/', views.doctor_appointments, name='doctor_appointments'),
    path('dashboard/doctor/patients/', views.doctor_patients, name='doctor_patients'),

    # --------- CUSTOM ADMIN UI (NOT Django /admin) ----------
    path('dabs-admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dabs-admin/doctors/applications/', views.admin_doctor_applications, name='admin_doctor_applications'),
    path('dabs-admin/doctors/pending/', views.admin_pending_doctors, name='admin_pending_doctors'),
    path('dabs-admin/doctors/', views.admin_doctors, name='admin_doctors'),
    path('dabs-admin/patients/', views.admin_patients, name='admin_patients'),
    path('dabs-admin/appointments/', views.admin_appointments, name='admin_appointments'),
    path('dabs-admin/appointments/export/csv/', views.admin_appointments_export, name='admin_appointments_export'),
    path('dabs-admin/reports/', views.admin_reports, name='admin_reports'),
    path('dabs-admin/settings/', views.admin_settings, name='admin_settings'),
    path('dabs-admin/logs/', views.admin_logs, name='admin_logs'),
]
