# exams/templatetags/exam_extras.py

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Dictionary dan qiymat olish uchun filter"""
    if dictionary and key:
        return dictionary.get(key)
    return 0