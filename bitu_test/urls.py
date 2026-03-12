from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path('nowayback-adminpanel/', admin.site.urls),
    path('admin-panel/', include('custom_admin.urls')),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('exams/', include('exams.urls')),
    path('sms-test/', include('eskiz_sms.urls')),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
   
