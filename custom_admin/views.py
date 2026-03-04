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

# ============================================
# ADMIN LOGIN
# ============================================
def admin_login(request):
    """Admin login sahifasi"""
    if request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff):
        return redirect('custom_admin:dashboard')
    
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





@admin_required
def direction_edit(request, direction_id=None):
    """Yo'nalish qo'shish yoki tahrirlash"""
    
    if direction_id:
        direction = get_object_or_404(Direction, id=direction_id)
        title = "Yo'nalishni tahrirlash"
    else:
        direction = Direction()
        title = "Yangi yo'nalish qo'shish"
    
    if request.method == 'POST':
        direction.name = request.POST.get('name')
        direction.code = request.POST.get('code')
        direction.description = request.POST.get('description', '')
        direction.is_active = request.POST.get('is_active') == 'on'
        direction.save()
        
        messages.success(request, f"Yo'nalish muvaffaqiyatli saqlandi!")
        return redirect('custom_admin:directions')
    
    context = {
        'direction': direction,
        'title': title,
    }
    
    return render(request, 'admin_panel/direction_edit.html', context)




@admin_required
def direction_delete(request, direction_id):
    """Yo'nalishni o'chirish"""
    
    direction = get_object_or_404(Direction, id=direction_id)
    
    # Bog'liq ma'lumotlarni tekshirish
    students_count = Profile.objects.filter(direction=direction).count()
    questions_count = Question.objects.filter(direction=direction).count()
    
    if students_count > 0 or questions_count > 0:
        messages.error(request, f"Bu yo'nalishga bog'liq {students_count} talaba va {questions_count} savol bor. Avval ularni o'chiring!")
        return redirect('custom_admin:directions')
    
    if request.method == 'POST':
        direction.delete()
        messages.success(request, f"Yo'nalish o'chirildi!")
        return redirect('custom_admin:directions')
    
    context = {
        'direction': direction,
    }
    
    return render(request, 'admin_panel/direction_delete.html', context)




@admin_required
def questions_list(request):
    """Savollar ro'yxati"""
    
    # Filter va qidiruv
    direction_id = request.GET.get('direction', '')
    search_query = request.GET.get('search', '')
    
    questions = Question.objects.all().select_related('direction').order_by('-created_at')
    
    if direction_id:
        questions = questions.filter(direction_id=direction_id)
    
    if search_query:
        questions = questions.filter(text__icontains=search_query)
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(questions, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    directions = Direction.objects.filter(is_active=True)
    
    context = {
        'questions': page_obj,
        'directions': directions,
        'selected_direction': int(direction_id) if direction_id else None,
        'search_query': search_query,
    }
    
    return render(request, 'admin_panel/questions.html', context)




@admin_required
def question_edit(request, question_id=None):
    """Savol qo'shish yoki tahrirlash"""
    
    if question_id:
        question = get_object_or_404(Question, id=question_id)
        title = "Savolni tahrirlash"
    else:
        question = Question()
        title = "Yangi savol qo'shish"
    
    if request.method == 'POST':
        question.direction_id = request.POST.get('direction')
        question.text = request.POST.get('text')
        question.option_a = request.POST.get('option_a')
        question.option_b = request.POST.get('option_b')
        question.option_c = request.POST.get('option_c')
        question.option_d = request.POST.get('option_d')
        question.correct_answer = request.POST.get('correct_answer')
        question.explanation = request.POST.get('explanation', '')
        question.is_active = request.POST.get('is_active') == 'on'
        question.save()
        
        messages.success(request, f"Savol muvaffaqiyatli saqlandi!")
        return redirect('custom_admin:questions')
    
    directions = Direction.objects.filter(is_active=True)
    
    context = {
        'question': question,
        'directions': directions,
        'title': title,
    }
    
    return render(request, 'admin_panel/question_edit.html', context)





@admin_required
def question_delete(request, question_id):
    """Savolni o'chirish"""
    
    question = get_object_or_404(Question, id=question_id)
    
    if request.method == 'POST':
        question.delete()
        messages.success(request, f"Savol o'chirildi!")
        return redirect('custom_admin:questions')
    
    context = {
        'question': question,
    }
    
    return render(request, 'admin_panel/question_delete.html', context)





@admin_required
def results_list(request):
    """Test natijalari ro'yxati"""
    
    # Filterlar
    direction_id = request.GET.get('direction', '')
    result_type = request.GET.get('result', '')  # passed, failed, all
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    results = TestResult.objects.filter(is_completed=True).select_related('user', 'direction').order_by('-completed_at')
    
    if direction_id:
        results = results.filter(direction_id=direction_id)
    
    if result_type == 'passed':
        results = results.filter(is_passed=True)
    elif result_type == 'failed':
        results = results.filter(is_passed=False)
    
    if date_from:
        results = results.filter(completed_at__date__gte=date_from)
    
    if date_to:
        results = results.filter(completed_at__date__lte=date_to)
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(results, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    directions = Direction.objects.filter(is_active=True)
    
    context = {
        'results': page_obj,
        'directions': directions,
        'selected_direction': int(direction_id) if direction_id else None,
        'selected_result': result_type,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'admin_panel/results.html', context)





@admin_required
def result_detail(request, result_id):
    """Test natijasi tafsiloti"""
    
    result = get_object_or_404(TestResult, id=result_id)
    answers = UserAnswer.objects.filter(test_result=result).select_related('question')
    
    context = {
        'result': result,
        'answers': answers,
    }
    
    return render(request, 'admin_panel/result_detail.html', context)