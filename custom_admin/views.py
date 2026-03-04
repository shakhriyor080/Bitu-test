from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from .decorators import admin_required

# Accounts modellari
from accounts.models import User, Profile, Direction, SMSVerification

# Exams modellari
from exams.models import Question, TestResult, UserAnswer


from decouple import config



def admin_login(request):
    """Admin login sahifasi"""
    if request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff):
        return redirect('custom_admin:dashboard')
    
    # .env dan admin ma'lumotlarini olish (agar kerak bo'lsa)
    admin_phone = config('ADMIN_PHONE', default='')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Telefon raqam yoki username bilan kirish
        user = authenticate(request, username=username, password=password)
        
        if user is not None and (user.is_superuser or user.is_staff):
            login(request, user)
            messages.success(request, f"Xush kelibsiz, {user.phone_number}!")
            return redirect('custom_admin:dashboard')
        else:
            messages.error(request, "Telefon raqam yoki parol xato, yoki siz admin emassiz")
    
    return render(request, 'admin_panel/login.html')

def admin_logout(request):
    logout(request)
    messages.success(request, "Tizimdan chiqdingiz")
    return redirect('custom_admin:login')




@admin_required
def dashboard(request):
    """Admin dashboard - statistika"""
    
    # Umumiy statistika
    total_users = User.objects.count()
    total_students = Profile.objects.count()
    total_directions = Direction.objects.filter(is_active=True).count()
    total_questions = Question.objects.filter(is_active=True).count()
    
    # Test natijalari
    total_tests = TestResult.objects.filter(is_completed=True).count()
    passed_tests = TestResult.objects.filter(is_completed=True, is_passed=True).count()
    failed_tests = total_tests - passed_tests
    
    # Oxirgi 7 kundagi testlar
    last_week = timezone.now() - timedelta(days=7)
    recent_tests = TestResult.objects.filter(completed_at__gte=last_week).count()
    
    # Yo'nalishlar bo'yicha statistika
    direction_stats = []
    for direction in Direction.objects.filter(is_active=True)[:]:
        students = Profile.objects.filter(direction=direction).count()
        tests = TestResult.objects.filter(direction=direction, is_completed=True).count()
        direction_stats.append({
            'name': direction.name,
            'students': students,
            'tests': tests
        })
    
    # Oxirgi 10 ta foydalanuvchi
    recent_users = User.objects.order_by('-date_joined')[:10]
    
    # Oxirgi 10 ta test natijalari
    recent_results = TestResult.objects.filter(is_completed=True).select_related('user', 'direction').order_by('-completed_at')[:10]
    
    context = {
        'total_users': total_users,
        'total_students': total_students,
        'total_directions': total_directions,
        'total_questions': total_questions,
        'total_tests': total_tests,
        'passed_tests': passed_tests,
        'failed_tests': failed_tests,
        'recent_tests': recent_tests,
        'direction_stats': direction_stats,
        'recent_users': recent_users,
        'recent_results': recent_results,
    }
    
    return render(request, 'admin_panel/dashboard.html', context)






@admin_required
def users_list(request):
    """Barcha foydalanuvchilar ro'yxati"""
    
    # Qidiruv
    search_query = request.GET.get('search', '')
    if search_query:
        users = User.objects.filter(
            Q(phone_number__icontains=search_query) |
            Q(profile__first_name__icontains=search_query) |
            Q(profile__last_name__icontains=search_query)
        ).distinct().order_by('-date_joined')
    else:
        users = User.objects.all().order_by('-date_joined')
    
    # Pagination (10 tadan)
    from django.core.paginator import Paginator
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'users': page_obj,
        'search_query': search_query,
        'total': users.count()
    }
    
    return render(request, 'admin_panel/users.html', context)




@admin_required
def user_detail(request, user_id):
    """Foydalanuvchi haqida batafsil"""
    
    user = get_object_or_404(User, id=user_id)
    
    # Profil ma'lumotlari
    try:
        profile = user.profile
    except Profile.DoesNotExist:
        profile = None
    
    # Test natijalari
    test_results = TestResult.objects.filter(user=user).order_by('-completed_at')
    
    context = {
        'user_obj': user,
        'profile': profile,
        'test_results': test_results,
    }
    
    return render(request, 'admin_panel/user_detail.html', context)



@admin_required
def directions_list(request):
    """Yo'nalishlar ro'yxati"""
    
    directions = Direction.objects.all().order_by('name')
    
    # Har bir yo'nalishdagi studentlar soni
    for direction in directions:
        direction.students_count = Profile.objects.filter(direction=direction).count()
        direction.questions_count = Question.objects.filter(direction=direction).count()
    
    context = {
        'directions': directions,
    }
    
    return render(request, 'admin_panel/directions.html', context)



