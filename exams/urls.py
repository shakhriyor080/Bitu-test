from django.urls import path
from . import views

app_name = 'exams'

urlpatterns = [
    path('instructions/', views.test_instructions, name='instructions'),
    path('take/', views.take_test, name='take_test'),
    path('save-progress/', views.save_test_progress, name='save_progress'),
    path('result/<int:result_id>/', views.test_result, name='result'),
]