from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView,
    LoginView,
    VerifyOTPView,
    RequestPasswordResetView,
    ResetPasswordView,
    ChangePasswordView,
    UserProfileView,
    VerifyLoginOTPView,
    SendEmailView,
    SetDecoyPasswordView
)

urlpatterns = [
    path('register', RegisterView.as_view(), name='register'),
    path('login', LoginView.as_view(), name='login'),
    path('verify-login-otp', VerifyLoginOTPView.as_view(), name='verify_login_otp'),
    path('token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('verify-otp', VerifyOTPView.as_view(), name='verify_otp'),
    path('request-password-reset', RequestPasswordResetView.as_view(), name='request_password_reset'),
    path('reset-password', ResetPasswordView.as_view(), name='reset_password'),
    path('change-password', ChangePasswordView.as_view(), name='change_password'),
    path('profile', UserProfileView.as_view(), name='user_profile'),
    path('send-email', SendEmailView.as_view(), name='send_email'),
    path('set-decoy-password', SetDecoyPasswordView.as_view(), name='set_decoy_password'),
]