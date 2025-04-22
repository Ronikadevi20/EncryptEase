from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PasswordViewSet, shared_password_view

router = DefaultRouter()
router.register(r'', PasswordViewSet, basename='password')

urlpatterns = [
    path('', include(router.urls)),
    path('shared/<uuid:token>/', shared_password_view, name='shared-password'),
]