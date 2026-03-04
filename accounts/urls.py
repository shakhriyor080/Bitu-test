# accounts/urls.py

from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('verify-sms/', views.verify_sms, name='verify_sms'),
    path('login/', views.login_view, name='login'),
    path('login-verify/', views.login_verify, name='login_verify'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('resend-sms/', views.resend_sms, name='resend_sms'), 
]