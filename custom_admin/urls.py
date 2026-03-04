from django.urls import path
from . import views

app_name = 'custom_admin'

urlpatterns = [
    # Login/Logout
    path('login/', views.admin_login, name='login'),
    path('logout/', views.admin_logout, name='logout'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Users
    path('users/', views.users_list, name='users'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    
    # Directions
    path('directions/', views.directions_list, name='directions'),
   
]