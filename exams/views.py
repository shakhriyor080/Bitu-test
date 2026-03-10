# exams/views.py

import json
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Count
from .models import Question, TestResult, UserAnswer
from accounts.models import Profile, Subject


@login_required
def test_instructions(request):
    """Test qoidalari sahifasi"""
    if not request.user.profile_completed:
        messages.warning(request, "Avval profilingizni to'ldiring")
        return redirect('accounts:profile')
    
    # Foydalanuvchining oldingi test natijalarini tekshirish
    completed_tests = TestResult.objects.filter(
        user=request.user, 
        is_completed=True
    ).order_by('-completed_at')
    
    can_retake = False
    if completed_tests.exists():
        latest_test = completed_tests.first()
        
        if not latest_test.can_retake:
            messages.warning(
                request, 
                "Siz testni allaqachon topshirgansiz. Qayta topshirish uchun administrator bilan bog'lanishingiz kerak."
            )
        else:
            messages.info(request, "Sizga testni qayta topshirishga ruxsat berildi. Omad!")
            can_retake = True
    
    try:
        profile = request.user.profile
        direction = profile.direction
        
        # Fanlar bo'yicha savollar sonini tekshirish
        subjects = Subject.objects.filter(is_active=True)
        subject_data = []
        total_available = 0
        
        for subject in subjects:
            count = Question.objects.filter(
                direction=direction, 
                subject=subject, 
                is_active=True
            ).count()
            subject_data.append({
                'name': subject.name,
                'count': count,
                'id': subject.id
            })
            total_available += count
        
        if total_available < 60:
            messages.error(request, f"Test uchun yetarli savollar mavjud emas.")
            return redirect('accounts:dashboard')
            
    except Profile.DoesNotExist:
        messages.error(request, "Profilingiz topilmadi")
        return redirect('accounts:profile')
    
    context = {
        'direction': direction,
        'question_count': 60,
        'max_score': 90,
        'passing_score': 15,
        'total_questions_available': total_available,
        'can_retake': can_retake,
        'has_completed_test': completed_tests.exists(),
        'subjects': subject_data,
    }
    return render(request, 'exams/test_instructions.html', context)


@login_required
def take_test(request):
    """Test topshirish - TUZATILGAN VERSIYA"""
    if not request.user.profile_completed:
        messages.warning(request, "Avval profilingizni to'ldiring")
        return redirect('accounts:profile')
    
    # Foydalanuvchining oldingi test natijalarini tekshirish
    completed_tests = TestResult.objects.filter(
        user=request.user, 
        is_completed=True
    ).order_by('-completed_at')
    
    if completed_tests.exists():
        latest_test = completed_tests.first()
        
        if not latest_test.can_retake:
            messages.error(
                request, 
                "Siz testni allaqachon topshirgansiz. Qayta topshirish mumkin emas."
            )
            return redirect('accounts:dashboard')
        else:
            # Ruxsat bo'lsa, eski testlarni o'chirish
            completed_tests.delete()
            messages.info(request, "Yangi test boshlamoqdasiz. Omad!")
    
    # 🔴 MUHIM: test_result o'zgaruvchisini oldindan e'lon qilish
    test_result = None
    selected_questions = []
    
    # Yakunlanmagan testni tekshirish
    try:
        test_result = TestResult.objects.get(
            user=request.user,
            is_completed=False
        )
        print(f"🔵 Mavjud test topildi: {test_result.id}")
        
        # 🔴 Sessiyadan savollar ID larini olish
        question_ids = request.session.get(f'test_questions_{test_result.id}')
        
        if question_ids:
            # Sessiyadan savollarni olish
            questions = Question.objects.filter(id__in=question_ids, is_active=True)
            # Berilgan tartibda saqlash
            question_dict = {q.id: q for q in questions}
            selected_questions = [question_dict[qid] for qid in question_ids if qid in question_dict]
            print(f"🔵 Sessiyadan {len(selected_questions)} ta savol olindi")
        else:
            # Agar sessiyada savollar bo'lmasa, xatolik
            messages.error(request, "Test ma'lumotlari topilmadi. Qayta boshlang.")
            return redirect('exams:instructions')
            
    except TestResult.DoesNotExist:
        # 🔴 YANGI TEST - birinchi marta boshlash
        print("🆕 Yangi test boshlanmoqda")
        
        direction = request.user.profile.direction
        
        # Fanlar bo'yicha savollarni olish
        subjects = Subject.objects.filter(is_active=True)
        
        for subject in subjects:
            subject_questions = list(Question.objects.filter(
                direction=direction,
                subject=subject,
                is_active=True
            ))
            
            if len(subject_questions) < 15:
                selected_questions.extend(subject_questions)
            else:
                selected_questions.extend(random.sample(subject_questions, 15))
        
        # Agar jami 60 tadan kam bo'lsa, qolganini to'ldirish
        if len(selected_questions) < 60:
            remaining = 60 - len(selected_questions)
            other_questions = list(Question.objects.filter(
                direction=direction,
                is_active=True
            ).exclude(
                id__in=[q.id for q in selected_questions]
            ))
            
            if other_questions:
                selected_questions.extend(random.sample(
                    other_questions, 
                    min(remaining, len(other_questions))
                ))
        
        # Savollarni aralashtirish
        random.shuffle(selected_questions)
        
        # 🔴 Yangi test result yaratish
        test_result = TestResult.objects.create(
            user=request.user,
            direction=direction,
            total_questions=60,
            can_retake=False
        )
        print(f"✅ Yangi test yaratildi: {test_result.id}")
        
        # 🔴 Savollarni sessiyaga saqlash
        question_ids = [q.id for q in selected_questions]
        request.session[f'test_questions_{test_result.id}'] = question_ids
        print(f"💾 {len(question_ids)} ta savol sessiyaga saqlandi")
        
    except TestResult.MultipleObjectsReturned:
        # Bir nechta yakunlanmagan test bo'lsa, hammasini o'chirib, qayta boshlash
        TestResult.objects.filter(user=request.user, is_completed=False).delete()
        messages.warning(request, "Texnik xatolik. Test qayta boshlanmoqda.")
        return redirect('exams:take_test')
    
    # 🔴 MUHIM: test_result mavjudligini tekshirish
    if test_result is None:
        messages.error(request, "Test yaratishda xatolik yuz berdi.")
        return redirect('exams:instructions')
    
    if request.method == 'POST':
        # POST so'rovi - testni yakunlash
        answers = json.loads(request.POST.get('answers', '{}'))
        correct_count = 0
        
        test_result.answers.all().delete()
        
        for question_id, answer in answers.items():
            try:
                question = Question.objects.get(id=question_id, is_active=True)
                is_correct = (answer == question.correct_answer)
                if is_correct:
                    correct_count += 1
                
                UserAnswer.objects.create(
                    test_result=test_result,
                    question=question,
                    selected_answer=answer,
                    is_correct=is_correct
                )
            except Question.DoesNotExist:
                continue
        
        test_result.correct_answers = correct_count
        test_result.calculate_result()
        test_result.is_completed = True
        test_result.completed_at = timezone.now()
        test_result.save()
        
        # Sessiyani tozalash
        if f'test_questions_{test_result.id}' in request.session:
            del request.session[f'test_questions_{test_result.id}']
        if f'test_answers_{test_result.id}' in request.session:
            del request.session[f'test_answers_{test_result.id}']
        
        messages.success(request, "Test yakunlandi!")
        return redirect('exams:result', result_id=test_result.id)
    
    # Har bir savolga indeks qo'shish
    for i, question in enumerate(selected_questions):
        question.question_index = i + 1
    
    # Sessiyadan saqlangan javoblarni olish
    saved_answers = request.session.get(f'test_answers_{test_result.id}', {})
    
    context = {
        'questions': selected_questions,
        'test_result': test_result,
        'saved_answers': json.dumps(saved_answers),
        'total_questions': 60,
    }
    return render(request, 'exams/take_test.html', context)


@csrf_exempt
@login_required
def save_test_progress(request):
    """Test progressini saqlash (AJAX)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            test_result_id = data.get('test_result_id')
            answers = data.get('answers', {})
            
            # TestResult mavjudligini tekshirish
            test_result = get_object_or_404(TestResult, id=test_result_id, user=request.user)
            
            # Sessiyaga saqlash
            request.session[f'test_answers_{test_result_id}'] = answers
            request.session.modified = True
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


@login_required
def test_result(request, result_id):
    """Test natijasi sahifasi"""
    test_result = get_object_or_404(TestResult, id=result_id, user=request.user)
    
    answers = test_result.answers.select_related('question').all()
    
    context = {
        'test_result': test_result,
        'answers': answers,
        'total_questions': 60,
        'max_score': 90,
        'passing_score': 15
    }
    return render(request, 'exams/result.html', context)