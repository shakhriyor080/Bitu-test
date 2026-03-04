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
    """Test qoidalari sahifasi"""
    if not request.user.profile_completed:
        messages.warning(request, "Avval profilingizni to'ldiring")
        return redirect('accounts:profile')
    
    # 🔴 TESTNI QAYTA TOPSHIRISH TEKSHIRUVI
    # Foydalanuvchining oldingi test natijalarini tekshirish
    completed_tests = TestResult.objects.filter(
        user=request.user, 
        is_completed=True
    ).order_by('-completed_at')
    
    can_retake = False
    if completed_tests.exists():
        latest_test = completed_tests.first()
        
        # Agar qayta topshirishga ruxsat bo'lmasa
        if not latest_test.can_retake:
            messages.warning(
                request, 
                "Siz testni allaqachon topshirgansiz. Qayta topshirish uchun administrator bilan bog'lanishingiz kerak."
            )
            # return redirect('accounts:dashboard')  # Izoh olib tashlansa, to'g'ridan-to'g'ri qaytaradi
        else:
            # Ruxsat bo'lsa, xabar chiqaramiz
            messages.info(request, "Sizga testni qayta topshirishga ruxsat berildi. Omad!")
            can_retake = True
    
    # Foydalanuvchi yo'nalishini olish
    try:
        profile = request.user.profile
        direction = profile.direction
        
        # Barcha yo'nalishlar uchun umumiy savollar sonini tekshirish
        question_count = Question.objects.filter(is_active=True).count()
        if question_count < 60:
            messages.error(request, f"Test uchun yetarli savollar mavjud emas. Mavjud: {question_count} ta (60 ta kerak)")
            return redirect('accounts:dashboard')
            
    except Profile.DoesNotExist:
        messages.error(request, "Profilingiz topilmadi")
        return redirect('accounts:profile')
    
    context = {
        'direction': direction,
        'question_count': 60,
        'max_score': 90,
        'passing_score': 15,
        'total_questions_available': Question.objects.filter(is_active=True).count(),
        'can_retake': can_retake,
        'has_completed_test': completed_tests.exists(),
    }
    return render(request, 'exams/test_instructions.html', context)


@login_required
def take_test(request):
    """Test topshirish"""
    if not request.user.profile_completed:
        messages.warning(request, "Avval profilingizni to'ldiring")
        return redirect('accounts:profile')
    
    # 🔴 TESTNI QAYTA TOPSHIRISH TEKSHIRUVI
    # Foydalanuvchining oldingi test natijalarini tekshirish
    completed_tests = TestResult.objects.filter(
        user=request.user, 
        is_completed=True
    ).order_by('-completed_at')
    
    if completed_tests.exists():
        latest_test = completed_tests.first()
        
        # Agar qayta topshirishga ruxsat bo'lmasa
        if not latest_test.can_retake:
            messages.error(
                request, 
                "Siz testni allaqachon topshirgansiz. Qayta topshirish mumkin emas."
            )
            return redirect('accounts:dashboard')
        else:
            # Ruxsat bo'lsa, eski testlarni o'chirish (ixtiyoriy)
            # Agar eski testlarni saqlab qolish kerak bo'lsa, bu qatorni o'chiring
            # Agar saqlab qolish kerak bo'lsa, quyidagi qatorni izohga oling
            completed_tests.delete()
            messages.info(request, "Yangi test boshlamoqdasiz. Omad!")
    
    # Yakunlanmagan testni tekshirish
    try:
        test_result = TestResult.objects.get(
            user=request.user,
            is_completed=False
        )
    except TestResult.DoesNotExist:
        # Yangi test yaratish
        test_result = TestResult.objects.create(
            user=request.user,
            direction=request.user.profile.direction,
            total_questions=60,
            can_retake=False  # Yangi testda ruxsat yo'q
        )
    except TestResult.MultipleObjectsReturned:
        # Bir nechta yakunlanmagan test bo'lsa, hammasini o'chirib, yangisini yaratish
        TestResult.objects.filter(user=request.user, is_completed=False).delete()
        test_result = TestResult.objects.create(
            user=request.user,
            direction=request.user.profile.direction,
            total_questions=60,
            can_retake=False
        )
    
    if request.method == 'POST':
        # POST so'rovi - testni yakunlash
        answers = json.loads(request.POST.get('answers', '{}'))
        correct_count = 0
        
        # Eski javoblarni tozalash
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
        
        # Natijani hisoblash va saqlash
        test_result.correct_answers = correct_count
        test_result.calculate_result()
        test_result.is_completed = True
        test_result.completed_at = timezone.now()
        test_result.save()
        
        # Sessiyani tozalash
        if f'test_answers_{test_result.id}' in request.session:
            del request.session[f'test_answers_{test_result.id}']
        
        messages.success(request, "Test yakunlandi!")
        return redirect('exams:result', result_id=test_result.id)
    
    # GET so'rovi - testni ko'rsatish
    # Barcha aktiv savollarni olish
    all_questions = list(Question.objects.filter(is_active=True))
    
    if len(all_questions) < 60:
        messages.error(request, f"Test uchun yetarli savollar mavjud emas. Mavjud: {len(all_questions)} ta (60 ta kerak)")
        return redirect('accounts:dashboard')
    
    # 60 ta savolni tasodifiy tanlash
    selected_questions = random.sample(all_questions, 60)
    # Savollarni aralashtirish
    random.shuffle(selected_questions)
    
    # Sessiyadan saqlangan javoblarni olish
    saved_answers = request.session.get(f'test_answers_{test_result.id}', {})
    
    context = {
        'questions': selected_questions,
        'test_result': test_result,
        'saved_answers': json.dumps(saved_answers),
        'total_questions': 60,
        'total_available': len(all_questions)
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
    
    # Javoblarni olish
    answers = test_result.answers.select_related('question').all()
    
    context = {
        'test_result': test_result,
        'answers': answers,
        'total_questions': 60,
        'max_score': 90,
        'passing_score': 15
    }
    return render(request, 'exams/result.html', context)