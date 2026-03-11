from datetime import timedelta

from decouple import config
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decorators import admin_required
from accounts.models import Direction, Profile, Subject, User
from exams.models import DirectionSubjectConfig, Question, TestResult


def admin_login(request):
    if request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff):
        return redirect('custom_admin:dashboard')

    config('ADMIN_PHONE', default='')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None and (user.is_superuser or user.is_staff):
            login(request, user)
            messages.success(request, f"Xush kelibsiz, {user.phone_number}!")
            return redirect('custom_admin:dashboard')
        messages.error(request, "Telefon raqam yoki parol xato, yoki siz admin emassiz")

    return render(request, 'admin_panel/login.html')


def admin_logout(request):
    logout(request)
    messages.success(request, "Tizimdan chiqdingiz")
    return redirect('custom_admin:login')


@admin_required
def dashboard(request):
    total_users = User.objects.count()
    total_students = Profile.objects.count()
    total_directions = Direction.objects.filter(is_active=True).count()
    total_questions = Question.objects.filter(is_active=True).count()

    total_tests = TestResult.objects.filter(is_completed=True).count()
    passed_tests = TestResult.objects.filter(is_completed=True, is_passed=True).count()
    failed_tests = total_tests - passed_tests

    last_week = timezone.now() - timedelta(days=7)
    recent_tests = TestResult.objects.filter(completed_at__gte=last_week).count()

    direction_stats = []
    for direction in Direction.objects.filter(is_active=True):
        students = Profile.objects.filter(direction=direction).count()
        tests = TestResult.objects.filter(direction=direction, is_completed=True).count()
        direction_stats.append({'name': direction.name, 'students': students, 'tests': tests})

    recent_users = User.objects.order_by('-date_joined')[:10]
    recent_results = (
        TestResult.objects.filter(is_completed=True)
        .select_related('user', 'direction')
        .order_by('-completed_at')[:10]
    )

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
    search_query = request.GET.get('search', '')
    if search_query:
        users = (
            User.objects.filter(
                Q(phone_number__icontains=search_query)
                | Q(profile__first_name__icontains=search_query)
                | Q(profile__last_name__icontains=search_query)
            )
            .distinct()
            .order_by('-date_joined')
        )
    else:
        users = User.objects.all().order_by('-date_joined')

    from django.core.paginator import Paginator

    paginator = Paginator(users, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'users': page_obj,
        'search_query': search_query,
        'total': users.count(),
    }
    return render(request, 'admin_panel/users.html', context)


@admin_required
def user_detail(request, user_id):
    user = get_object_or_404(User, id=user_id)

    try:
        profile = user.profile
    except Profile.DoesNotExist:
        profile = None

    test_results = TestResult.objects.filter(user=user).order_by('-completed_at')

    context = {
        'user_obj': user,
        'profile': profile,
        'test_results': test_results,
    }
    return render(request, 'admin_panel/user_detail.html', context)


@admin_required
def directions_list(request):
    directions = Direction.objects.all().order_by('name')

    for direction in directions:
        direction.students_count = Profile.objects.filter(direction=direction).count()

        config_qs = DirectionSubjectConfig.objects.filter(direction=direction, is_active=True)
        direction.configured_subjects = config_qs.count()
        direction.configured_total = sum(c.question_count for c in config_qs)
        direction.questions_count = Question.objects.filter(
            subject_id__in=config_qs.values('subject_id'),
            is_active=True,
        ).count()

    context = {'directions': directions}
    return render(request, 'admin_panel/directions.html', context)


@admin_required
def direction_exam_settings(request, direction_id):
    direction = get_object_or_404(Direction, id=direction_id)
    subjects = Subject.objects.filter(is_active=True).order_by('name')

    existing_map = {
        item.subject_id: item
        for item in DirectionSubjectConfig.objects.filter(direction=direction)
    }

    if request.method == 'POST':
        prepared = []
        errors = []

        for idx, subject in enumerate(subjects, start=1):
            raw = (request.POST.get(f'count_{subject.id}', '0') or '0').strip()
            try:
                count = int(raw)
            except ValueError:
                count = 0

            if count < 0:
                count = 0

            available = Question.objects.filter(subject=subject, is_active=True).count()

            if count > available:
                errors.append(f"{subject.name}: kiritilgan son ({count}) mavjud savollardan ({available}) katta.")

            prepared.append({'subject': subject, 'count': count, 'order': idx, 'available': available})

        total_selected = sum(item['count'] for item in prepared)
        if total_selected <= 0:
            errors.append("Kamida bitta fan uchun savol sonini 1 yoki undan katta kiriting.")

        if errors:
            for err in errors:
                messages.error(request, err)
        else:
            with transaction.atomic():
                for item in prepared:
                    if item['count'] > 0:
                        DirectionSubjectConfig.objects.update_or_create(
                            direction=direction,
                            subject=item['subject'],
                            defaults={
                                'question_count': item['count'],
                                'order': item['order'],
                                'is_active': True,
                            },
                        )
                    else:
                        DirectionSubjectConfig.objects.filter(
                            direction=direction,
                            subject=item['subject'],
                        ).delete()

            messages.success(request, "Yo'nalish uchun test fanlari va savollar soni saqlandi.")
            return redirect('custom_admin:direction_settings', direction_id=direction.id)

    rows = []
    for subject in subjects:
        available = Question.objects.filter(subject=subject, is_active=True).count()
        cfg = existing_map.get(subject.id)
        rows.append(
            {
                'subject': subject,
                'available': available,
                'selected_count': cfg.question_count if cfg else 0,
            }
        )

    configured_total = sum(r['selected_count'] for r in rows)

    context = {
        'direction': direction,
        'rows': rows,
        'configured_total': configured_total,
    }
    return render(request, 'admin_panel/direction_settings.html', context)
