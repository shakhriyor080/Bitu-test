from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, SMSVerification, Direction, Profile
from exams.models import Question, TestResult, UserAnswer
from import_export.admin import ImportExportModelAdmin, ExportActionModelAdmin








class UserAdmin(BaseUserAdmin, ImportExportModelAdmin):
    inlines = []
    list_display = ('phone_number', 'profile_completed', 'is_staff', 'date_joined')
    list_filter = ('profile_completed', 'is_staff', 'is_superuser', 'is_active')
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'profile_completed', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'password1', 'password2', 'is_active', 'is_staff')}
        ),
    )
    search_fields = ('phone_number',)
    ordering = ('-date_joined',)
    filter_horizontal = ('groups', 'user_permissions',)

# Profile Inline
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profil'
    fk_name = 'user'

# Yangi UserAdmin ga ProfileInline qo'shamiz
UserAdmin.inlines = [ProfileInline]

# User modelini registratsiya qilish
admin.site.register(User, UserAdmin)

@admin.register(SMSVerification)
class SMSVerificationAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'code', 'created_at', 'is_verified')
    list_filter = ('is_verified', 'created_at')
    search_fields = ('phone_number',)
    readonly_fields = ('code', 'created_at')

@admin.register(Direction)
class DirectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    prepopulated_fields = {'code': ('name',)}

@admin.register(Profile)
class ProfileAdmin(ImportExportModelAdmin):
    list_display = ('full_name', 'user', 'direction', 'referral_code', 'created_at')
    list_filter = ('direction', 'created_at')
    search_fields = ('first_name', 'last_name', 'user__phone_number', 'referral_code')
    raw_id_fields = ('user',)
    
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Ism Familiya'


# Exams admin
@admin.register(Question)
class QuestionAdmin(ImportExportModelAdmin):
    list_display = ('short_text', 'direction', 'correct_answer', 'is_active', 'created_at')
    list_filter = ('direction', 'is_active', 'correct_answer')
    search_fields = ('text',)
    list_editable = ('is_active',)
    list_per_page = 20
    
    def short_text(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    short_text.short_description = 'Savol'


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ('user_phone', 'direction', 'score', 'is_passed', 'completed_at')
    list_filter = ('is_passed', 'direction', 'completed_at')
    search_fields = ('user__phone_number', 'direction__name')
    readonly_fields = ('score', 'total_questions', 'correct_answers', 'started_at', 'completed_at')
    date_hierarchy = 'completed_at'
    
    def user_phone(self, obj):
        return obj.user.phone_number
    user_phone.short_description = 'Foydalanuvchi'
    user_phone.admin_order_field = 'user__phone_number'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'direction')



@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ('test_result', 'question_short', 'selected_answer', 'is_correct')
    list_filter = ('is_correct',)
    search_fields = ('test_result__user__phone_number', 'question__text')
    
    def question_short(self, obj):
        return str(obj.question)[:30]
    question_short.short_description = 'Savol'




from .models import Subject

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    list_editable = ('is_active',)
    prepopulated_fields = {'code': ('name',)}

