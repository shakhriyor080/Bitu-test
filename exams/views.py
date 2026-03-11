# exams/views.py

import json
import random
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import Profile, Subject
from .models import DirectionSubjectConfig, Question, TestResult, UserAnswer

DEFAULT_TOTAL_QUESTIONS = 60
DEFAULT_BLOCK_SIZE = 15
DEFAULT_PAGE_COUNT = DEFAULT_TOTAL_QUESTIONS // DEFAULT_BLOCK_SIZE
DISPLAY_KEYS = ['A', 'B', 'C', 'D']


def _get_subject_counts():
    data = []
    for subject in Subject.objects.filter(is_active=True).order_by('name'):
        count = Question.objects.filter(subject=subject, is_active=True).count()
        data.append({'id': subject.id, 'name': subject.name, 'count': count})
    return data


def _get_custom_configs(direction):
    configs = (
        DirectionSubjectConfig.objects.filter(
            direction=direction,
            is_active=True,
            question_count__gt=0,
            subject__is_active=True,
        )
        .select_related('subject')
        .order_by('order', 'id')
    )
    return list(configs)


def _build_pages_from_custom(configs):
    pages = []
    total_questions = 0

    for cfg in configs:
        required = cfg.question_count
        if required <= 0:
            continue

        qs = list(Question.objects.filter(subject=cfg.subject, is_active=True))

        if len(qs) < required:
            return None, 0, f"{cfg.subject.name} fanida kamida {required} ta aktiv savol bo'lishi kerak."

        selected = random.sample(qs, required)
        random.shuffle(selected)

        pages.append({
            'subject_id': cfg.subject_id,
            'subject_name': cfg.subject.name,
            'questions': selected,
        })
        total_questions += required

    if total_questions <= 0:
        return None, 0, "Sozlamada kamida bitta fan uchun savol soni berilishi kerak."

    return pages, total_questions, None


def _build_default_pages():
    pools = []
    for subject in Subject.objects.filter(is_active=True).order_by('id'):
        questions = list(Question.objects.filter(subject=subject, is_active=True))
        if questions:
            random.shuffle(questions)
            pools.append({'subject': subject, 'questions': questions})

    pages = []
    while len(pages) < DEFAULT_PAGE_COUNT:
        if not pools:
            break

        pool = max(pools, key=lambda p: len(p['questions']))
        if len(pool['questions']) < DEFAULT_BLOCK_SIZE:
            break

        selected = [pool['questions'].pop() for _ in range(DEFAULT_BLOCK_SIZE)]
        random.shuffle(selected)

        pages.append({
            'subject_id': pool['subject'].id,
            'subject_name': pool['subject'].name,
            'questions': selected,
        })

    if len(pages) < DEFAULT_PAGE_COUNT:
        return None, 0, "Standart rejim uchun 15 talik 4 ta blokga yetarli savol yo'q."

    return pages, DEFAULT_TOTAL_QUESTIONS, None


def _materialize_pages_from_session(session_pages):
    pages = []
    all_questions = []

    for page in session_pages:
        question_ids = page.get('question_ids', [])
        subject_id = page.get('subject_id')

        if not question_ids:
            return None, 0

        questions = list(
            Question.objects.filter(id__in=question_ids, is_active=True).select_related('subject')
        )
        q_map = {q.id: q for q in questions}
        ordered = [q_map[qid] for qid in question_ids if qid in q_map]

        if len(ordered) != len(question_ids):
            return None, 0

        subject_name = ordered[0].subject.name if ordered and ordered[0].subject else 'Umumiy fan'
        pages.append({
            'subject_id': subject_id,
            'subject_name': subject_name,
            'questions': ordered,
        })
        all_questions.extend(ordered)

    return pages, len(all_questions)


def _ensure_option_map(request, test_result, subject_pages):
    session_key = f'test_option_map_{test_result.id}'
    option_map = request.session.get(session_key, {})
    changed = False

    for page in subject_pages:
        for question in page['questions']:
            qid = str(question.id)

            if qid not in option_map:
                original_keys = DISPLAY_KEYS.copy()
                random.shuffle(original_keys)
                option_map[qid] = {
                    display_key: original_key
                    for display_key, original_key in zip(DISPLAY_KEYS, original_keys)
                }
                changed = True

            mapping = option_map[qid]
            shuffled_options = []
            for display_key in DISPLAY_KEYS:
                original_key = mapping.get(display_key, display_key)
                text = getattr(question, f"option_{original_key.lower()}")
                shuffled_options.append({
                    'display_key': display_key,
                    'text': text,
                })
            question.shuffled_options = shuffled_options

    if changed:
        request.session[session_key] = option_map
        request.session.modified = True

    return option_map


@login_required
def test_instructions(request):
    if not request.user.profile_completed:
        messages.warning(request, "Avval profilingizni to'ldiring")
        return redirect('accounts:profile')

    completed_tests = TestResult.objects.filter(user=request.user, is_completed=True).order_by('-completed_at')

    can_retake = False
    if completed_tests.exists():
        latest = completed_tests.first()
        if not latest.can_retake:
            messages.warning(request, "Siz testni allaqachon topshirgansiz. Qayta topshirish uchun administrator bilan bog'laning.")
        else:
            messages.info(request, "Sizga testni qayta topshirishga ruxsat berildi. Omad!")
            can_retake = True

    try:
        direction = request.user.profile.direction
    except Profile.DoesNotExist:
        messages.error(request, "Profilingiz topilmadi")
        return redirect('accounts:profile')

    custom_configs = _get_custom_configs(direction)
    subjects_display = []

    if custom_configs:
        total_required = 0
        for cfg in custom_configs:
            available = Question.objects.filter(subject=cfg.subject, is_active=True).count()
            subjects_display.append({
                'id': cfg.subject_id,
                'name': cfg.subject.name,
                'count': available,
                'required': cfg.question_count,
            })
            total_required += cfg.question_count

            if available < cfg.question_count:
                messages.error(
                    request,
                    f"{cfg.subject.name} fanida yetarli savol yo'q: kerak {cfg.question_count}, mavjud {available}.",
                )
                return redirect('accounts:dashboard')

        question_count = total_required
    else:
        subject_data = _get_subject_counts()
        total_available = sum(s['count'] for s in subject_data)
        capacity = sum(s['count'] // DEFAULT_BLOCK_SIZE for s in subject_data)

        if total_available < DEFAULT_TOTAL_QUESTIONS or capacity < DEFAULT_PAGE_COUNT:
            messages.error(request, "Testni boshlash uchun jami 60 ta savol va 15 talik 4 ta blok kerak.")
            return redirect('accounts:dashboard')

        question_count = DEFAULT_TOTAL_QUESTIONS
        for s in subject_data:
            s['required'] = DEFAULT_BLOCK_SIZE
        subjects_display = subject_data

    context = {
        'direction': direction,
        'question_count': question_count,
        'max_score': question_count * 1.5,
        'passing_score': 15,
        'can_retake': can_retake,
        'has_completed_test': completed_tests.exists(),
        'subjects': subjects_display,
    }
    return render(request, 'exams/test_instructions.html', context)


@login_required
def take_test(request):
    if not request.user.profile_completed:
        messages.warning(request, "Avval profilingizni to'ldiring")
        return redirect('accounts:profile')

    completed_tests = TestResult.objects.filter(user=request.user, is_completed=True).order_by('-completed_at')
    if completed_tests.exists():
        latest = completed_tests.first()
        if not latest.can_retake:
            messages.error(request, "Siz testni allaqachon topshirgansiz. Qayta topshirish mumkin emas.")
            return redirect('accounts:dashboard')
        completed_tests.delete()
        messages.info(request, "Yangi test boshlamoqdasiz. Omad!")

    test_result = None
    subject_pages = []
    total_questions = 0

    try:
        test_result = TestResult.objects.get(user=request.user, is_completed=False)
        session_pages = request.session.get(f'test_subject_pages_{test_result.id}', [])
        subject_pages, total_questions = _materialize_pages_from_session(session_pages)

        if not subject_pages:
            messages.error(request, "Test ma'lumotlari topilmadi. Qayta boshlang.")
            return redirect('exams:instructions')

    except TestResult.DoesNotExist:
        direction = request.user.profile.direction
        custom_configs = _get_custom_configs(direction)

        if custom_configs:
            subject_pages, total_questions, err = _build_pages_from_custom(custom_configs)
        else:
            subject_pages, total_questions, err = _build_default_pages()

        if err:
            messages.error(request, err)
            return redirect('exams:instructions')

        test_result = TestResult.objects.create(
            user=request.user,
            direction=direction,
            total_questions=total_questions,
            can_retake=False,
        )

        request.session[f'test_subject_pages_{test_result.id}'] = [
            {
                'subject_id': page['subject_id'],
                'question_ids': [q.id for q in page['questions']],
            }
            for page in subject_pages
        ]
        request.session[f'test_questions_{test_result.id}'] = [q.id for p in subject_pages for q in p['questions']]
        request.session.modified = True

    except TestResult.MultipleObjectsReturned:
        TestResult.objects.filter(user=request.user, is_completed=False).delete()
        messages.warning(request, "Texnik xatolik. Test qayta boshlanmoqda.")
        return redirect('exams:take_test')

    option_map = _ensure_option_map(request, test_result, subject_pages)

    if request.method == 'POST':
        answers = json.loads(request.POST.get('answers', '{}'))
        correct_count = 0

        test_result.answers.all().delete()

        for question_id, answer in answers.items():
            if answer not in DISPLAY_KEYS:
                continue

            try:
                question = Question.objects.get(id=question_id, is_active=True)
            except Question.DoesNotExist:
                continue

            question_map = option_map.get(str(question_id), {})
            selected_original = question_map.get(answer, answer)

            is_correct = (selected_original == question.correct_answer)
            if is_correct:
                correct_count += 1

            UserAnswer.objects.create(
                test_result=test_result,
                question=question,
                selected_answer=selected_original,
                is_correct=is_correct,
            )

        test_result.correct_answers = correct_count
        test_result.calculate_result()
        test_result.is_completed = True
        test_result.completed_at = timezone.now()
        test_result.save()

        for key in [
            f'test_subject_pages_{test_result.id}',
            f'test_questions_{test_result.id}',
            f'test_answers_{test_result.id}',
            f'test_option_map_{test_result.id}',
        ]:
            if key in request.session:
                del request.session[key]

        messages.success(request, "Test yakunlandi!")
        return redirect('exams:result', result_id=test_result.id)

    index = 1
    for page_index, page in enumerate(subject_pages, start=1):
        page['page_number'] = page_index
        for q in page['questions']:
            q.question_index = index
            index += 1

    saved_answers = request.session.get(f'test_answers_{test_result.id}', {})

    context = {
        'subject_pages': subject_pages,
        'test_result': test_result,
        'saved_answers': json.dumps(saved_answers),
        'total_questions': total_questions,
        'total_pages': len(subject_pages),
    }
    return render(request, 'exams/take_test.html', context)


@login_required
def save_test_progress(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            test_result_id = data.get('test_result_id')
            answers = data.get('answers', {})

            get_object_or_404(TestResult, id=test_result_id, user=request.user)
            request.session[f'test_answers_{test_result_id}'] = answers
            request.session.modified = True
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


@login_required
def test_result(request, result_id):
    test_result = get_object_or_404(TestResult, id=result_id, user=request.user)
    answers = test_result.answers.select_related('question').all()

    context = {
        'test_result': test_result,
        'answers': answers,
        'total_questions': test_result.total_questions,
        'max_score': test_result.total_questions * 1.5,
        'passing_score': 15,
    }
    return render(request, 'exams/result.html', context)
