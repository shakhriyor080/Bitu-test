from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import User, SMSVerification, Profile, Direction
from .forms import PhoneNumberForm, SMSVerificationForm, ProfileForm
from exams.models import TestResult


from eskiz_sms.views import send_sms


def register(request):
    """
    Foydalanuvchini ro'yxatdan o'tkazish:
    1. Telefon raqamni olish
    2. SMS kod yaratish va yuborish
    3. Tasdiqlash sahifasiga yo'naltirish
    """
    if request.method == 'POST':
        form = PhoneNumberForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data['phone_number']
            
            # Telefon raqamni formatlash (agar kerak bo'lsa)
            # +998 bilan boshlanmasa, avtomatik qo'shish
            if not phone_number.startswith('+'):
                phone_number = '+998' + phone_number.replace(' ', '').replace('-', '')
            
            # Foydalanuvchini yaratish yoki mavjudini olish
            user, created = User.objects.get_or_create(phone_number=phone_number)
            
            # SMS tasdiqlash obyektini yaratish
            sms_verification, _ = SMSVerification.objects.get_or_create(
                phone_number=phone_number,
                defaults={'user': user if not created else None}
            )
            
            # 6 xonali tasodifiy kod yaratish
            code = sms_verification.generate_code()
            
            # 📱 Eskiz.uz orqali SMS yuborish
            message = f"BITU Test uchun tasdiqlash kodi: {code}"
            
            try:
                # SMS yuborishga urinish
                send_sms(phone_number, message)
                messages.success(request, f"SMS kod yuborildi. Kod: {code}")  # Test uchun ekranga chiqadi prop
            except Exception as e:
                # Agar SMS yuborishda xatolik bo'lsa, konsolga chiqaramiz
                print(f"SMS yuborishda xatolik: {e}")
                # Xatolik bo'lganda ham kodni ko'rsatamiz (test uchun)
                messages.warning(request, f"SMS yuborilmadi. Test kodi: {code}")
            
            # Telefon raqamni sessiyada saqlash
            request.session['verification_phone'] = phone_number
            
            return redirect('accounts:verify_sms')
    else:
        form = PhoneNumberForm()
    
    return render(request, 'accounts/register.html', {'form': form})





def verify_sms(request):
    """
    Foydalanuvchi kiritgan SMS kodni tekshirish:
    1. Sessiyadagi telefon raqamni olish
    2. Kiritilgan kodni tekshirish
    3. To'g'ri bo'lsa, foydalanuvchini tizimga kiritish
    """
    phone_number = request.session.get('verification_phone')
    if not phone_number:
        messages.error(request, "Avval telefon raqamingizni kiriting")
        return redirect('accounts:register')
    
    if request.method == 'POST':
        form = SMSVerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            
            try:
                # SMS kodni tekshirish
                sms_verification = SMSVerification.objects.get(
                    phone_number=phone_number,
                    code=code,
                    is_verified=False
                )
                
                # Kodni tasdiqlangan deb belgilash
                sms_verification.is_verified = True
                sms_verification.save()
                
                # Foydalanuvchini olish
                user, created = User.objects.get_or_create(phone_number=phone_number)
                
                # Foydalanuvchini tizimga kiritish
                login(request, user)
                
                # Sessiyani tozalash
                del request.session['verification_phone']
                
                messages.success(request, "Muvaffaqiyatli ro'yxatdan o'tdingiz!")
                
                # Profil to'ldirilmagan bo'lsa, profil sahifasiga yo'naltirish
                if not user.profile_completed:
                    return redirect('accounts:profile')
                return redirect('accounts:dashboard')
                
            except SMSVerification.DoesNotExist:
                messages.error(request, "Noto'g'ri kod yoki kod muddati tugagan")
    else:
        form = SMSVerificationForm()
    
    return render(request, 'accounts/verify_sms.html', {'form': form})





def login_view(request):
    """
    Foydalanuvchini tizimga kiritish:
    1. Telefon raqamni olish
    2. SMS kod yaratish va yuborish
    3. Tasdiqlash sahifasiga yo'naltirish
    """
    if request.method == 'POST':
        form = PhoneNumberForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data['phone_number']
            
            # Telefon raqamni formatlash
            if not phone_number.startswith('+'):
                phone_number = '+998' + phone_number.replace(' ', '').replace('-', '')
            
            try:
                # Foydalanuvchi mavjudligini tekshirish
                user = User.objects.get(phone_number=phone_number)
                
                # SMS tasdiqlash obyektini yaratish
                sms_verification = SMSVerification.objects.create(
                    user=user,
                    phone_number=phone_number
                )
                code = sms_verification.generate_code()
                
                # 📱 Eskiz.uz orqali SMS yuborish
                message = f"BITU Test uchun tasdiqlash kodi: {code}"
                
                try:
                    send_sms(phone_number, message)
                    messages.success(request, f"SMS kod yuborildi. Kod: {code}")  # Test uchun
                except Exception as e:
                    print(f"SMS yuborishda xatolik: {e}")
                    messages.warning(request, f"SMS yuborilmadi. Test kodi: {code}")
                
                # Telefon raqamni sessiyada saqlash
                request.session['login_phone'] = phone_number
                
                return redirect('accounts:login_verify')
                
            except User.DoesNotExist:
                messages.error(request, "Bu telefon raqam tizimda mavjud emas")
    else:
        form = PhoneNumberForm()
    
    return render(request, 'accounts/login.html', {'form': form})






def login_verify(request):
    """
    Login paytida SMS kodni tekshirish:
    1. Sessiyadagi telefon raqamni olish
    2. Kiritilgan kodni tekshirish
    3. To'g'ri bo'lsa, foydalanuvchini tizimga kiritish
    """
    phone_number = request.session.get('login_phone')
    if not phone_number:
        return redirect('accounts:login')
    
    if request.method == 'POST':
        form = SMSVerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            
            try:
                # SMS kodni tekshirish
                sms_verification = SMSVerification.objects.get(
                    phone_number=phone_number,
                    code=code,
                    is_verified=False
                )
                
                # Kodni tasdiqlash
                sms_verification.is_verified = True
                sms_verification.save()
                
                # Foydalanuvchini olish
                user = User.objects.get(phone_number=phone_number)
                
                # Tizimga kiritish
                login(request, user)
                
                # Sessiyani tozalash
                del request.session['login_phone']
                
                messages.success(request, "Muvaffaqiyatli kirdingiz!")
                
                # Profil to'ldirilmagan bo'lsa, profil sahifasiga yo'naltirish
                if not user.profile_completed:
                    return redirect('accounts:profile')
                return redirect('accounts:dashboard')
                
            except SMSVerification.DoesNotExist:
                messages.error(request, "Noto'g'ri kod")
    else:
        form = SMSVerificationForm()
    
    return render(request, 'accounts/verify_sms.html', {'form': form, 'login': True})




@login_required
def logout_view(request):
    """
    Foydalanuvchini tizimdan chiqarish
    """
    logout(request)
    messages.success(request, "Tizimdan chiqdingiz")
    return redirect('core:index')





@login_required
def profile_view(request):
    """
    Foydalanuvchi profilini to'ldirish:
    1. Ism, familiya
    2. Yo'nalish tanlash
    3. Referal kod
    """
    # Agar profil allaqachon to'ldirilgan bo'lsa, dashboardga yo'naltirish
    if request.user.profile_completed:
        return redirect('accounts:dashboard')
    
    # Profil mavjudligini tekshirish
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
            
            # Foydalanuvchi profilini to'ldirilgan deb belgilash
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
    """
    Foydalanuvchining shaxsiy kabineti:
    1. Profil ma'lumotlari
    2. Test natijalari
    3. Amallar (test topshirish, natijalarni ko'rish)
    """
    # Profil to'ldirilmagan bo'lsa, profil sahifasiga yo'naltirish
    if not request.user.profile_completed:
        return redirect('accounts:profile')
    
    try:
        profile = request.user.profile
        # Foydalanuvchining test natijalarini olish
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






@login_required
def resend_sms(request):
    """
    SMS kodni qayta yuborish (agar foydalanuvchi kodni olmagan bo'lsa)
    """
    # Telefon raqamni sessiyadan olish
    phone_number = request.session.get('verification_phone') or request.session.get('login_phone')
    
    if not phone_number:
        messages.error(request, "Telefon raqam topilmadi")
        return redirect('accounts:register')
    
    try:
        # Mavjud SMS tasdiqlash obyektini olish
        sms_verification = SMSVerification.objects.filter(
            phone_number=phone_number,
            is_verified=False
        ).latest('created_at')
        
        # Yangi kod yaratish
        code = sms_verification.generate_code()
        
        # 📱 SMS yuborish
        message = f"BITU Test uchun tasdiqlash kodi: {code}"
        
        try:
            send_sms(phone_number, message)
            messages.success(request, f"SMS kod qayta yuborildi. Kod: {code}")
        except Exception as e:
            print(f"SMS yuborishda xatolik: {e}")
            messages.warning(request, f"SMS yuborilmadi. Test kodi: {code}")
        
    except SMSVerification.DoesNotExist:
        messages.error(request, "SMS tasdiqlash ma'lumotlari topilmadi")
    
    # Qayerga qaytishni aniqlash
    if request.session.get('login_phone'):
        return redirect('accounts:login_verify')
    else:
        return redirect('accounts:verify_sms')