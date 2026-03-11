from django.urls import path
from . import views

app_name = 'custom_admin'

urlpatterns = [
    path('login/', views.admin_login, name='login'),
    path('logout/', views.admin_logout, name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('users/', views.users_list, name='users'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('directions/', views.directions_list, name='directions'),
    path('directions/<int:direction_id>/settings/', views.direction_exam_settings, name='direction_settings'),
]
