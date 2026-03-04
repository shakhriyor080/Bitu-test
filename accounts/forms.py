from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Profile, Direction

class PhoneNumberForm(forms.Form):
    phone_number = forms.CharField(
        label='Telefon raqam',
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+998652205545',
            'pattern': r'^\+?998?\d{9}$'
        })
    )

class SMSVerificationForm(forms.Form):
    code = forms.CharField(
        label='SMS kod',
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '123456',
            'pattern': r'\d{6}'
        })
    )

class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        label='Ism',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        label='Familiya',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    direction = forms.ModelChoiceField(
        label="Yo'nalish",
        queryset=Direction.objects.filter(is_active=True),
        empty_label="Yo'nalishni tanlang",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    referral_code = forms.CharField(
        label='Referal kod',
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Profile
        fields = ['first_name', 'last_name', 'direction', 'referral_code']