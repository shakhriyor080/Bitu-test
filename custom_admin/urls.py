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
    path('directions/add/', views.direction_edit, name='direction_add'),
    path('directions/<int:direction_id>/edit/', views.direction_edit, name='direction_edit'),
    path('directions/<int:direction_id>/delete/', views.direction_delete, name='direction_delete'),
    
    # Questions
    path('questions/', views.questions_list, name='questions'),
    path('questions/add/', views.question_edit, name='question_add'),
    path('questions/<int:question_id>/edit/', views.question_edit, name='question_edit'),
    path('questions/<int:question_id>/delete/', views.question_delete, name='question_delete'),
    
    # Results
    path('results/', views.results_list, name='results'),
    path('results/<int:result_id>/', views.result_detail, name='result_detail'),
]