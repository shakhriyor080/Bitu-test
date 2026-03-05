from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .models import User, SMSVerification, Profile, Direction
from .forms import PhoneNumberForm, SMSVerificationForm, ProfileForm
from exams.models import TestResult


from eskiz_sms.views import send_sms



def register(request):
    if request.method == 'POST':
        form = PhoneNumberForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data['phone_number']
            
         
            phone_number = format_phone_number(phone_number)
            
            # Foydalanuvchini yaratish yoki mavjudini olish
            user, created = User.objects.get_or_create(phone_number=phone_number)
      


            SMSVerification.objects.filter(
                phone_number=phone_number, 
                is_verified=False
            ).delete()
           

            sms_verification = SMSVerification.objects.create(
                user=user,
                phone_number=phone_number
            )
            
            # 6 xonali tasodifiy kod yaratish
            code = sms_verification.generate_code()
            
            #  Eskiz.uz orqali SMS yuborish
            message = f"BITU Test websaytiga kirishda telefon raqamingizni tasdiqlash uchun kod: {code}."
            
            try:
                # SMS yuborishga urinish
                send_sms(phone_number, message)
                messages.success(request, f"SMS kod yuborildi.")
            except Exception as e:
                print(f"SMS yuborishda xatolik: ")
                # Xatolik bo'lganda ham kodni ko'rsatish (test uchun)
                messages.warning(request, f"Test kodi: error ")
            
          
            request.session['verification_phone'] = phone_number
            request.session['verification_time'] = timezone.now().isoformat()
            
            return redirect('accounts:verify_sms')
    else:
        form = PhoneNumberForm()
    
    return render(request, 'accounts/register.html', {'form': form})





def format_phone_number(phone_number):
    """Telefon raqamni standart formatga keltirish"""
    # Bo'sh joylarni va tirelarni olib tashlash
    phone_number = phone_number.replace(' ', '').replace('-', '').replace('_', '')
    
    # +998 bilan boshlanmasa, qo'shish
    if not phone_number.startswith('+'):
        if phone_number.startswith('998'):
            phone_number = '+' + phone_number
        elif len(phone_number) == 9:  
            phone_number = '+998' + phone_number
        else:
            phone_number = '+998' + phone_number
    
    return phone_number





def verify_sms(request):
    phone_number = request.session.get('verification_phone')
    
    if not phone_number:
        messages.error(request, "Avval telefon raqamingizni kiriting")
        return redirect('accounts:register')
    
    # Telefon raqamni formatlash
    phone_number = format_phone_number(phone_number)
    
    # Vaqt cheklovi (5 daqiqa)
    verification_time = request.session.get('verification_time')
    if verification_time:
        try:
            sent_time = timezone.datetime.fromisoformat(verification_time)
            if timezone.now() > sent_time + timedelta(minutes=5):
                messages.error(request, "Kodning amal qilish muddati tugagan. Qayta urinib ko'ring.")
                return redirect('accounts:register')
        except:
            pass
    
    if request.method == 'POST':
        form = SMSVerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            
    
            try:
                # Eng oxirgi yaratilgan, tasdiqlanmagan SMSVerificationni olish
                sms_verification = SMSVerification.objects.filter(
                    phone_number=phone_number,
                    code=code,
                    is_verified=False
                ).latest('created_at')
                
                # Kodni tasdiqlangan deb belgilash
                sms_verification.is_verified = True
                sms_verification.save()
                
                # Foydalanuvchini olish
                user, created = User.objects.get_or_create(phone_number=phone_number)
                
                # Foydalanuvchini tizimga kiritish
                login(request, user)
                
                # Sessiyani tozalash
                if 'verification_phone' in request.session:
                    del request.session['verification_phone']
                if 'verification_time' in request.session:
                    del request.session['verification_time']
                
                messages.success(request, "Muvaffaqiyatli ro'yxatdan o'tdingiz!")
                
                # Profil to'ldirilmagan bo'lsa, profil sahifasiga yo'naltirish
                if not user.profile_completed:
                    return redirect('accounts:profile')
                return redirect('accounts:dashboard')
                
            except SMSVerification.DoesNotExist:
                messages.error(request, "Noto'g'ri kod")
            except SMSVerification.MultipleObjectsReturned:
                # Agar bir nechta bo'lsa, hammasini o'chirib, yangi kod so'rashni tavsiya qilish
                SMSVerification.objects.filter(
                    phone_number=phone_number,
                    is_verified=False
                ).delete()
                messages.error(request, "Texnik xatolik. Iltimos, qayta urinib ko'ring.")
                return redirect('accounts:register')
    else:
        form = SMSVerificationForm()
    
    return render(request, 'accounts/verify_sms.html', {'form': form})




def resend_sms(request):
    """SMS kodni qayta yuborish"""
    phone_number = request.session.get('verification_phone') or request.session.get('login_phone')
    
    if not phone_number:
        messages.error(request, "Telefon raqam topilmadi")
        return redirect('accounts:register')
    
    phone_number = format_phone_number(phone_number)
    
    try:
        # Eski, tasdiqlanmagan SMSVerificationlarni o'chirish
        SMSVerification.objects.filter(
            phone_number=phone_number, 
            is_verified=False
        ).delete()
        
        # Foydalanuvchini olish
        user = User.objects.filter(phone_number=phone_number).first()
        
        # Yangi SMSVerification yaratish
        sms_verification = SMSVerification.objects.create(
            user=user,
            phone_number=phone_number
        )
        
        # Yangi kod yaratish
        code = sms_verification.generate_code()
        
      
        message = f"BITU Test websaytiga kirishda telefon raqamingizni tasdiqlash uchun kod: {code}."
        
        try:
            send_sms(phone_number, message)
            messages.success(request, f"SMS kod qayta yuborildi.")
        except Exception as e:
            print(f"SMS yuborishda xatolik: {e}")
            messages.warning(request, f"Test kodi: {code}")
        
        # Vaqtni yangilash
        request.session['verification_time'] = timezone.now().isoformat()
        
    except Exception as e:
        messages.error(request, f"Xatolik yuz berdi: {e}")
    
    # Qayerga qaytishni aniqlash
    if request.session.get('login_phone'):
        return redirect('accounts:login_verify')
    else:
        return redirect('accounts:verify_sms')




def login_view(request):
    if request.method == 'POST':
        form = PhoneNumberForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data['phone_number']
            phone_number = format_phone_number(phone_number)
            
            try:
                # Foydalanuvchi mavjudligini tekshirish
                user = User.objects.get(phone_number=phone_number)
                
                # Eski SMSVerification larni o'chirish
                SMSVerification.objects.filter(
                    phone_number=phone_number, 
                    is_verified=False
                ).delete()
                
                # Yangi SMS tasdiqlash obyektini yaratish
                sms_verification = SMSVerification.objects.create(
                    user=user,
                    phone_number=phone_number
                )
                code = sms_verification.generate_code()
                
                # 📱 Eskiz.uz orqali SMS yuborish
                message = f"BITU Test websaytiga kirishda telefon raqamingizni tasdiqlash uchun kod: {code}."
                
                try:
                    send_sms(phone_number, message)
                    messages.success(request, f"SMS kod yuborildi.")
                except Exception as e:
                    print(f"SMS yuborishda xatolik: {e}")
                    messages.warning(request, f"Test kodi: {code}")
                
                # Telefon raqamni sessiyada saqlash
                request.session['login_phone'] = phone_number
                request.session['login_time'] = timezone.now().isoformat()
                
                return redirect('accounts:login_verify')
                
            except User.DoesNotExist:
                messages.error(request, "Bu telefon raqam tizimda mavjud emas")
    else:
        form = PhoneNumberForm()
    
    return render(request, 'accounts/login.html', {'form': form})


# ============================================
# Login SMS kodni tasdiqlash (Login Verify)
# ============================================
def login_verify(request):
    phone_number = request.session.get('login_phone')
    
    if not phone_number:
        return redirect('accounts:login')
    
    phone_number = format_phone_number(phone_number)
    
    # Vaqt cheklovi (5 daqiqa)
    login_time = request.session.get('login_time')
    if login_time:
        try:
            sent_time = timezone.datetime.fromisoformat(login_time)
            if timezone.now() > sent_time + timedelta(minutes=5):
                messages.error(request, "Kodning amal qilish muddati tugagan. Qayta urinib ko'ring.")
                return redirect('accounts:login')
        except:
            pass
    
    if request.method == 'POST':
        form = SMSVerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            
            try:
                # Eng oxirgi yaratilgan, tasdiqlanmagan SMSVerificationni olish
                sms_verification = SMSVerification.objects.filter(
                    phone_number=phone_number,
                    code=code,
                    is_verified=False
                ).latest('created_at')
                
                # Kodni tasdiqlash
                sms_verification.is_verified = True
                sms_verification.save()
                
                # Foydalanuvchini olish
                user = User.objects.get(phone_number=phone_number)
                
                # Tizimga kiritish
                login(request, user)
                
                # Sessiyani tozalash
                if 'login_phone' in request.session:
                    del request.session['login_phone']
                if 'login_time' in request.session:
                    del request.session['login_time']
                
                messages.success(request, "Muvaffaqiyatli kirdingiz!")
                
                # Profil to'ldirilmagan bo'lsa, profil sahifasiga yo'naltirish
                if not user.profile_completed:
                    return redirect('accounts:profile')
                return redirect('accounts:dashboard')
                
            except SMSVerification.DoesNotExist:
                messages.error(request, "Noto'g'ri kod")
            except SMSVerification.MultipleObjectsReturned:
                SMSVerification.objects.filter(
                    phone_number=phone_number,
                    is_verified=False
                ).delete()
                messages.error(request, "Texnik xatolik. Iltimos, qayta urinib ko'ring.")
                return redirect('accounts:login')
    else:
        form = SMSVerificationForm()
    
    return render(request, 'accounts/verify_sms.html', {'form': form, 'login': True})





# ============================================
# Qolgan viewlar (profile, dashboard, logout)
# ============================================
@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Tizimdan chiqdingiz")
    return redirect('core:index')


@login_required
def profile_view(request):
    if request.user.profile_completed:
        return redirect('accounts:dashboard')
    
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = None
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            
            request.user.profile_completed = True
            request.user.save()
            
            messages.success(request, "Profilingiz muvaffaqiyatli to'ldirildi!")
            return redirect('accounts:dashboard')
    else:
        form = ProfileForm(instance=profile)
    
    return render(request, 'accounts/profile.html', {
        'form': form,
        'phone_number': request.user.phone_number
    })


@login_required
def dashboard(request):
    if not request.user.profile_completed:
        return redirect('accounts:profile')
    
    try:
        profile = request.user.profile
        test_results = TestResult.objects.filter(user=request.user).order_by('-completed_at')
        latest_result = test_results.first()
    except Profile.DoesNotExist:
        profile = None
        test_results = []
        latest_result = None
    
    context = {
        'profile': profile,
        'test_results': test_results,
        'latest_result': latest_result,
    }
    return render(request, 'accounts/dashboard.html', context)