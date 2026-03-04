import json
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Question, TestResult, UserAnswer
from accounts.models import Profile

@login_required
def test_instructions(request):
    if not request.user.profile_completed:
        messages.warning(request, "Avval profilingizni to'ldiring")
        return redirect('accounts:profile')
    
    # Check if user already took the test
    if TestResult.objects.filter(user=request.user, is_completed=True).exists():
        messages.warning(request, "Siz testni allaqachon topshirgansiz")
        return redirect('accounts:dashboard')
    
    # Get user's direction (faqat ma'lumot uchun)
    try:
        profile = request.user.profile
        direction = profile.direction
        
        #  O'ZGARTIRISH: Barcha yo'nalishlar uchun umumiy savollar sonini tekshirish
        question_count = Question.objects.filter(is_active=True).count()
        if question_count < 60:
            messages.error(request, f"Test uchun yetarli savollar mavjud emas. ")  # Mavjud: {question_count} ta (60 ta kerak)
            return redirect('accounts:dashboard')
            
    except Profile.DoesNotExist:
        messages.error(request, "Profilingiz topilmadi")
        return redirect('accounts:profile')
    
    context = {
        'direction': direction,
        'question_count': 60,
        'max_score': 90,
        'passing_score': 15,
        'total_questions_available': Question.objects.filter(is_active=True).count()  # Jami mavjud savollar
    }
    return render(request, 'exams/test_instructions.html', context)


@login_required
def take_test(request):
    if not request.user.profile_completed:
        return redirect('accounts:profile')
    
    # Check if user already took the test
    if TestResult.objects.filter(user=request.user, is_completed=True).exists():
        messages.warning(request, "Siz testni allaqachon topshirgansiz")
        return redirect('accounts:dashboard')
    
    # Check for incomplete test
    test_result, created = TestResult.objects.get_or_create(
        user=request.user,
        is_completed=False,
        defaults={
            'direction': request.user.profile.direction,  # Yo'nalishni saqlaymiz (ma'lumot uchun)
            'total_questions': 60
        }
    )
    
    if request.method == 'POST':
        # Save answers
        answers = json.loads(request.POST.get('answers', '{}'))
        correct_count = 0
        
        # Clear previous answers
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
        
        # Calculate and save result
        test_result.correct_answers = correct_count
        test_result.calculate_result()
        test_result.is_completed = True
        test_result.completed_at = timezone.now()
        test_result.save()
        
        messages.success(request, "Test yakunlandi!")
        return redirect('exams:result', result_id=test_result.id)
    
    #  ASOSIY O'ZGARTIRISH: Barcha yo'nalishlar uchun umumiy savollar
    # Barcha aktiv savollarni olish
    all_questions = list(Question.objects.filter(is_active=True))
    
    # Agar savollar 60 tadan kam bo'lsa, xatolik chiqarish
    if len(all_questions) < 60:
        messages.error(request, f"Test uchun yetarli savollar mavjud emas. ") #  Mavjud: {len(all_questions)} ta (60 ta kerak)
        return redirect('accounts:dashboard')
    
    #  Random tanlash: 60 ta savolni tasodifiy tanlash
    selected_questions = random.sample(all_questions, 60)
    
    #  Random aralashtirish (qo'shimcha)
    random.shuffle(selected_questions)
    
    # Check if there's saved progress in session
    saved_answers = request.session.get(f'test_answers_{test_result.id}', {})
    
    context = {
        'questions': selected_questions,  # Random tanlangan 60 ta savol
        'test_result': test_result,
        'saved_answers': json.dumps(saved_answers),
        'total_questions': 60,
        'total_available': len(all_questions)  # Jami mavjud savollar soni
    }
    return render(request, 'exams/take_test.html', context)


@csrf_exempt
@login_required
def save_test_progress(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        test_result_id = data.get('test_result_id')
        answers = data.get('answers', {})
        
        # Save to session
        request.session[f'test_answers_{test_result_id}'] = answers
        request.session.modified = True
        
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def test_result(request, result_id):
    test_result = get_object_or_404(TestResult, id=result_id, user=request.user)
    
    # Get answers with questions
    answers = test_result.answers.select_related('question').all()
    
    context = {
        'test_result': test_result,
        'answers': answers,
        'total_questions': 60,
        'max_score': 90,
        'passing_score': 15
    }
    return render(request, 'exams/result.html', context)