from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def admin_required(view_func):
    """Faqat adminlar kirishi mumkin bo'lgan view'lar uchun decorator"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Iltimos, tizimga kiring")
            return redirect('custom_admin:login')
        
        if not request.user.is_superuser and not request.user.is_staff:
            messages.error(request, "Sizda admin panelga kirish huquqi yo'q")
            return redirect('core:index')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view