# exams/models.py

from django.db import models
from django.contrib.auth import get_user_model
from accounts.models import Direction

from accounts.models import Subject

User = get_user_model()


class Question(models.Model):
    # Mavjud maydonlar
    direction = models.ForeignKey(Direction, on_delete=models.CASCADE, related_name='questions', verbose_name="Yo'nalish")
    text = models.TextField(verbose_name="Savol matni")
    option_a = models.CharField(max_length=500, verbose_name="A variant")
    option_b = models.CharField(max_length=500, verbose_name="B variant")
    option_c = models.CharField(max_length=500, verbose_name="C variant")
    option_d = models.CharField(max_length=500, verbose_name="D variant")
    correct_answer = models.CharField(
        max_length=1,
        choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')],
        verbose_name="To'g'ri javob"
    )
    explanation = models.TextField(blank=True, null=True, verbose_name="Izoh")
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
  
    subject = models.ForeignKey(
        Subject, 
        on_delete=models.CASCADE, 
        related_name='questions', 
        verbose_name="Fan",
        null=True,  
        blank=True
    )
    
    class Meta:
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.text[:50]
    
    def get_options(self):
        return {
            'A': self.option_a,
            'B': self.option_b,
            'C': self.option_c,
            'D': self.option_d,
        }


class TestResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_results')
    direction = models.ForeignKey(Direction, on_delete=models.SET_NULL, null=True)
    score = models.FloatField(default=0, verbose_name="Ball")
    total_questions = models.IntegerField(default=0, verbose_name="Jami savollar")
    correct_answers = models.IntegerField(default=0, verbose_name="To'g'ri javoblar")
    is_passed = models.BooleanField(default=False, verbose_name="O'tdi")
    is_completed = models.BooleanField(default=False, verbose_name="Yakunlangan")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    can_retake = models.BooleanField(default=False, verbose_name="Qayta topshirishga ruxsat")
    
    class Meta:
        verbose_name = "Test natijasi"
        verbose_name_plural = "Test natijalari"
        ordering = ['-completed_at']
    
    def __str__(self):
        return f"{self.user.phone_number} - {self.score} ball"
    
    def calculate_result(self):
        self.total_questions = 60
        self.score = self.correct_answers * 1.5
        self.is_passed = self.score >= 15
        return self.is_passed


class UserAnswer(models.Model):
    test_result = models.ForeignKey(TestResult, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answer = models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')])
    is_correct = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Foydalanuvchi javobi"
        verbose_name_plural = "Foydalanuvchi javoblari"
    
    def __str__(self):
        return f"{self.question.text[:30]} - {self.selected_answer}"