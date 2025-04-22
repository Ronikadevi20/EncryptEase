from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf.urls.static import static
from django.conf import settings

schema_view = get_schema_view(
   openapi.Info(
      title="Job Application Manager API",
      default_version='v1',
      description="API documentation for Job Application Manager",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@jobapps.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
      path('admin/', admin.site.urls),
      path('api/auth/', include('core.urls')),
      path('api/applications/', include('applications.urls')),
      path('api/passwords/', include('passwords.urls')),
      path('api/bills/', include('bills.urls')),
      path('api/documents/', include('documents.urls')),
      path('api/settings/', include('settings_app.urls')),
      path('api/trash/', include('trash.urls')),

      # Swagger UI
      path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
      # ReDoc UI
      path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
      # Raw schema (JSON)
      path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)