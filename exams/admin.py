from django.contrib import admin
from django.contrib import messages
from django.urls import path
from django.shortcuts import redirect, get_object_or_404
from django.utils.html import format_html
from .models import Question, TestResult, UserAnswer



class QuestionAdmin(admin.ModelAdmin):
    list_display = ('short_text', 'direction', 'correct_answer', 'is_active', 'created_at')
    list_filter = ('direction', 'is_active', 'correct_answer')
    search_fields = ('text',)
    list_editable = ('is_active',)
    list_per_page = 20
    
    def short_text(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    short_text.short_description = 'Savol'



class TestResultAdmin(admin.ModelAdmin):
    list_display = (
        'user_phone', 
        'direction', 
        'score', 
        'is_passed', 
        'completed_at', 
        'can_retake', 
        'action_buttons'
    )
    list_filter = ('is_passed', 'direction', 'completed_at', 'can_retake')
    search_fields = ('user__phone_number', 'direction__name')
    readonly_fields = ('score', 'total_questions', 'correct_answers', 'started_at', 'completed_at')
    list_editable = ('can_retake',)
    list_per_page = 20
    date_hierarchy = 'completed_at'
    actions = ['allow_retake', 'disallow_retake']
    
    fieldsets = (
        ("Foydalanuvchi ma'lumotlari", {
            'fields': ('user', 'direction')
        }),
        ("Test natijalari", {
            'fields': ('score', 'total_questions', 'correct_answers', 'is_passed')
        }),
        ("Vaqt ma'lumotlari", {
            'fields': ('started_at', 'completed_at')
        }),
        ("Ruxsatlar", {
            'fields': ('can_retake',),
            'description': 'Agar "Qayta topshirishga ruxsat" belgilansa, foydalanuvchi testni qayta topshirishi mumkin'
        }),
    )
    
    def user_phone(self, obj):
        return obj.user.phone_number
    user_phone.short_description = 'Foydalanuvchi'
    user_phone.admin_order_field = 'user__phone_number'
    
    def action_buttons(self, obj):
        """Admin panelda maxsus tugmalar"""
        if obj.is_completed:
            if obj.can_retake:
                return format_html(
                    '<a class="button" href="{}" style="background: #28a745; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none; margin-right: 5px;">✅ Ruxsat berilgan</a>',
                    f'/admin/exams/testresult/{obj.id}/toggle-retake/'
                )
            else:
                return format_html(
                    '<a class="button" href="{}" style="background: #ffc107; color: black; padding: 5px 10px; border-radius: 4px; text-decoration: none;">🔄 Ruxsat berish</a>',
                    f'/admin/exams/testresult/{obj.id}/toggle-retake/'
                )
        return "Test yakunlanmagan"
    action_buttons.short_description = 'Amallar'
    action_buttons.allow_tags = True
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:result_id>/toggle-retake/',
                 self.admin_site.admin_view(self.toggle_retake),
                 name='toggle-retake'),
        ]
        return custom_urls + urls
    
    def toggle_retake(self, request, result_id):
        """Qayta topshirish ruxsatini o'zgartirish"""
        test_result = get_object_or_404(TestResult, id=result_id)
        test_result.can_retake = not test_result.can_retake
        test_result.save()
        
        if test_result.can_retake:
            messages.success(request, f"{test_result.user.phone_number} uchun testni qayta topshirishga ruxsat berildi!")
        else:
            messages.warning(request, f"{test_result.user.phone_number} uchun testni qayta topshirish ruxsati olib tashlandi!")
        
        return redirect('/admin/exams/testresult/')
    
    def allow_retake(self, request, queryset):
        updated = queryset.update(can_retake=True)
        self.message_user(request, f"{updated} ta testga qayta topshirish ruxsati berildi.")
    allow_retake.short_description = "Tanlangan testlarni qayta topshirishga ruxsat berish"
    
    def disallow_retake(self, request, queryset):
        updated = queryset.update(can_retake=False)
        self.message_user(request, f"{updated} ta testdan qayta topshirish ruxsati olib tashlandi.")
    disallow_retake.short_description = "Tanlangan testlardan ruxsatni olib tashlash"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'direction')



class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ('test_result', 'question_short', 'selected_answer', 'is_correct')
    list_filter = ('is_correct',)
    search_fields = ('test_result__user__phone_number', 'question__text')
    list_per_page = 20
    
    def question_short(self, obj):
        return str(obj.question)[:30]
    question_short.short_description = 'Savol'


from django.contrib.admin import site
from django.contrib.admin.sites import AlreadyRegistered

try:
    # Agar oldin ro'yxatdan o'tgan bo'lsa, o'chirish
    site.unregister(Question)
except:
    pass

try:
    site.unregister(TestResult)
except:
    pass

try:
    site.unregister(UserAnswer)
except:
    pass

# Yangidan ro'yxatdan o'tkazish
admin.site.register(Question, QuestionAdmin)
admin.site.register(TestResult, TestResultAdmin)
admin.site.register(UserAnswer, UserAnswerAdmin)