from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.conf import settings
import pyotp
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError
from .models import UserProfile
from .serializers import (
    UserSerializer, 
    RegisterSerializer, 
    ChangePasswordSerializer,
    RequestOTPSerializer,
    VerifyOTPSerializer,
    ResetPasswordSerializer
)
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from bs4 import BeautifulSoup
from django.utils.html import format_html


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

    @swagger_auto_schema(
        operation_description="Register a new user account",
        request_body=RegisterSerializer,
        security=[],
        responses={
            201: openapi.Response(
                description="User registered successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description='Success message'
                        ),
                    }
                )
            ),
            400: openapi.Response(
                description="Bad request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
        },
        tags=['Authentication'],
    )
    def post(self, request, *args, **kwargs):
        print("AUTH SIGNUPS", request.data)
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            print("AUTH SIGNUPS", e)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print("AUTH SIGNUPS", e)
            return Response({"error": "Invalid data provided."}, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        print("User registered successfully")
        
        # Generate OTP code
        profile = user.profile
        otp_code = profile.generate_otp_code()  # Generate OTP code directly
        # HTML message for registration email
        html_message = f"""
        <html>
          <body style="font-family: Arial, sans-serif; background-color: #f8f9fa; padding: 20px; color: #333;">
            <div style="max-width: 600px; margin: auto; background-color: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 30px;">
              <h2 style="color: #007bff;">Welcome to EncryptEase, {user.username} 👋</h2>
              <p>Thank you for registering with <strong>EncryptEase</strong>.</p>
              <p>To complete your registration, please verify your email address by verifying the OTP:</p>
            <div style="background-color: #e9ecef; padding: 15px; border-radius: 5px; text-align: center; margin: 20px 0;">
                <h3 style="font-weight: bold;">🔐 OTP Code: {otp_code}</h3>
            </div>
              <p>If you did not initiate this registration, you can safely ignore this email.</p>
              <hr style="margin: 30px 0;">
              <p style="font-size: 14px; color: #777;">Best regards,<br>The EncryptEase Team</p>
            </div>
          </body>
        </html>
        """

        # Send verification email
        send_mail(
            subject='[EncryptEase] Successful Registration – Verify Your Email',
            message=f"Hi {user.username},\n\nPlease verify your email by clicking the link: {verification_link}",  # Fallback plain text
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
            html_message=html_message
        )

        return Response({
            "message": "User registered successfully. Please verify your email with the link sent."
        }, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    permission_classes = (permissions.AllowAny,)

    @swagger_auto_schema(
        operation_description="Authenticate user and get JWT tokens",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email', 'password'],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING),
                'password': openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        security=[],
        responses={
            200: openapi.Response(
                description="Successful authentication",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'refresh': openapi.Schema(type=openapi.TYPE_STRING),
                        'access': openapi.Schema(type=openapi.TYPE_STRING),
                        'user': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'email': openapi.Schema(type=openapi.TYPE_STRING),
                                'username': openapi.Schema(type=openapi.TYPE_STRING),
                                # Add other user fields as needed
                            }
                        ),
                        'decoy': openapi.Schema(
                            type=openapi.TYPE_BOOLEAN,
                            description='True if logged in with decoy password'
                        ),
                    }
                )
            ),
            # ... keep other responses the same ...
        },
        tags=['Authentication'],
    )
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response(
                {"error": "Both email and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
            profile = user.profile
            
            # First check if it's a decoy password
            if profile.decoy_password and profile.check_decoy_password(password):
                # Generate tokens for decoy login
                refresh = RefreshToken.for_user(user)
                user_data = UserSerializer(user).data
                user_data['decoy'] = True  # Add decoy flag to user data


                # send email to notify user that some has loged in with decoy mode please change password
                html_message = f"""
                <html>
                  <body style="font-family: Arial, sans-serif; background-color: #f8f9fa; padding: 20px; color: #333;">
                    <h2 style="font-weight: bold;">🚨 Decoy Login Detected</h2>
                    <p style="margin-bottom: 20px;">Hi {user.username},</p>
                    <p style="margin-bottom: 20px;">Someone has logged in with a decoy password.</p>
                    <p style="margin-bottom: 20px;">Please change your password to secure your account.</p>
                    <p style="margin-bottom: 20px;">Best regards,<br>The EncryptEase Team</p>
                  </body>
                </html>
                """
                send_mail(
                    subject='[EncryptEase] Decoy Login Detected',
                    message=f"Hi {user.username},\n\nYou have logged in with a decoy password. Please change your password to secure your account.",  # Fallback plain text
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                    html_message=html_message
                )

                # remove the decoy password
                profile.decoy_password = None
                profile.save()
                
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': user_data,
                    'decoy': True  # Also include at root level for easy access
                }, status=status.HTTP_200_OK)
            
            # Normal authentication flow
            auth_user = authenticate(request, username=user.username, password=password)
            
            if auth_user is None:
                return Response(
                    {"error": "Invalid credentials"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check if the user's email has been verified
            if not profile.otp_verified:
                return Response(
                    {"error": "Email not verified. Please verify your email first."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Generate and send OTP for every login attempt
            otp_code = profile.generate_otp_code()
            
            # Send OTP email
            html_message = f"""
            <html>
              <body style="font-family: Arial, sans-serif; background-color: #f8f9fa; padding: 20px; color: #333;">
                <div style="max-width: 600px; margin: auto; background-color: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 30px;">
                  <h2 style="color: #007bff;">Login Verification for EncryptEase</h2>
                  <p>Hi {user.username},</p>
                  <p>Here is your login verification OTP code:</p>
                  <div style="background-color: #e9ecef; padding: 15px; border-radius: 5px; text-align: center; margin: 20px 0;">
                    <h3 style="font-weight: bold;">🔐 OTP Code: {otp_code}</h3>
                  </div>
                  <p>This code is valid for a limited time. Please do not share it with anyone.</p>
                  <p>If you didn't request this login, please secure your account immediately.</p>
                  <hr style="margin: 30px 0;">
                  <p style="font-size: 14px; color: #777;">Stay secure,<br>The EncryptEase Team</p>
                </div>
              </body>
            </html>
            """

            send_mail(
                subject='[EncryptEase] Login Verification OTP',
                message=f"Hi {user.username},\n\nHere is your login verification OTP code: {otp_code}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
                html_message=html_message
            )
            
            return Response({
                "message": "OTP sent to your registered email. Please verify to complete login.",
                "email": user.email,
                "requires_otp": True
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except ObjectDoesNotExist:
            return Response(
                {"error": "User profile not found"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class VerifyOTPView(APIView):
    permission_classes = (permissions.AllowAny,)
    
    @swagger_auto_schema(
        operation_description="Verify OTP code for email verification",
        request_body=VerifyOTPSerializer,
        responses={
            200: openapi.Response(
                description="Email verified successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid OTP code",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            404: openapi.Response(
                description="User not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
        },
        tags=['Authentication'],
    )
    def post(self, request):
        print("Received request to verify OTP", request.data)
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            user = User.objects.get(email=serializer.validated_data['email'])
            profile = user.profile
            
            if profile.verify_otp(serializer.validated_data['otp_code']):
                profile.otp_verified = True
                profile.save()
                
                return Response({
                    "message": "Email verified successfully. You can now login."
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "error": "Invalid OTP code"
                }, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({
                "error": "User not found"
            }, status=status.HTTP_404_NOT_FOUND)

class VerifyLoginOTPView(APIView):
    permission_classes = (permissions.AllowAny,)
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            user = User.objects.get(email=serializer.validated_data['email'])
            profile = user.profile
            
            if profile.verify_otp(serializer.validated_data['otp_code']):
                # Generate tokens only after OTP verification
                refresh = RefreshToken.for_user(user)
                print("Generated tokens:", refresh)
                
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': UserSerializer(user).data
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "error": "Invalid OTP code"
                }, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({
                "error": "User not found"
            }, status=status.HTTP_404_NOT_FOUND)
            

class RequestPasswordResetView(APIView):
    permission_classes = (permissions.AllowAny,)
    
    def post(self, request):
        email = request.data.get('email', None)  # Ensure you get the email properly
        
        if not email:
            return Response(
                {"error": "Email is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
            profile = user.profile
            
            # Generate OTP for password reset
            otp_code = profile.generate_otp_code()
            
            # Create a professional email message
            subject = '[EncryptEase] Password Reset OTP'
            message = format_html("""
                <h2 style="color: #333;">Password Reset Request</h2>
                <p>Hi {username},</p>
                <p>We received a request to reset your password. Here is your OTP code:</p>
                <h3 style="color: #007BFF;">{otp_code}</h3>
                <p>If you didn't request a password reset, please ignore this email.</p>
                <p>Thank you,<br>Your EncryptEase Team</p>
                <footer style="font-size: 0.9em; color: #888;">
                    <p>This email was sent to {email}. If you have any questions, please contact support.</p>
                </footer>
            """, username=user.username, otp_code=otp_code, email=user.email)

            # Send password reset email with HTML content
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
                html_message=message  # Use HTML message
            )

            return Response({
                "message": "Password reset OTP sent to email.",
                "email": user.email
            }, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            # Return success even if user not found for security reasons
            return Response({
                "message": "If the email exists in our system, a password reset OTP has been sent."
            }, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    permission_classes = (permissions.AllowAny,)
    
    def post(self, request):
        print(request.data)
        email = request.data.get('email')
        otp_code = request.data.get('code')
        new_password = request.data.get('newPassword')
        
        if not all([email, otp_code, new_password]):
            return Response(
                {"error": "All fields are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
            profile = user.profile
            
            if profile.verify_otp(otp_code):
                user.set_password(new_password)
                user.save()
                return Response({
                    "message": "Password reset successfully"
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "error": "Invalid OTP code"
                }, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({
                "error": "User not found"
            }, status=status.HTTP_404_NOT_FOUND)

class ChangePasswordView(generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = (permissions.IsAuthenticated,)
    
    @swagger_auto_schema(
        operation_description="Change user password",
        request_body=ChangePasswordSerializer,
        responses={
            200: openapi.Response(
                description="Password updated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: openapi.Response(
                description="Bad request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'old_password': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
        },
        tags=['User'],
    )
    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        # Check old password
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({"old_password": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)
        
        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            "message": "Password updated successfully"
        }, status=status.HTTP_200_OK)

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)
    
    @swagger_auto_schema(
        operation_description="Retrieve current user profile",
        responses={
            200: openapi.Response(
                description="User profile data",
                schema=UserSerializer
            ),
        },
        tags=['User'],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Update current user profile",
        request_body=UserSerializer,
        responses={
            200: openapi.Response(
                description="Updated user profile data",
                schema=UserSerializer
            ),
            400: openapi.Response(
                description="Bad request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'field_name': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
        },
        tags=['User'],
    )
    def put(self, request, *args, **kwargs):
        print(request.data)
        return super().put(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Partial update current user profile",
        request_body=UserSerializer,
        responses={
            200: openapi.Response(
                description="Updated user profile data",
                schema=UserSerializer
            ),
            400: openapi.Response(
                description="Bad request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'field_name': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
        },
        tags=['User'],
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
    
    def get_object(self):
        return self.request.user

class SendEmailView(APIView):
    permission_classes = (permissions.AllowAny,)

    @swagger_auto_schema(
        operation_description="Send an email through the platform",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['subject', 'message', 'recipients'],
            properties={
                'subject': openapi.Schema(type=openapi.TYPE_STRING, description='Email subject'),
                'message': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='HTML email body content',
                    example="<html><body><h1>Hello</h1><p>This is an HTML email</p></body></html>"
                ),
                'recipients': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING),
                    description='List of recipient email addresses'
                ),
            },
        ),
        security=[],
        responses={
            200: openapi.Response(
                description="Email sent successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'recipients': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(type=openapi.TYPE_STRING))
                        },
                )
            ),
            400: openapi.Response(
                description="Bad request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={'error': openapi.Schema(type=openapi.TYPE_STRING)}
                )
            ),
        },
        tags=['Utils'],
    )
    def post(self, request):
        subject = request.data.get('subject')
        html_message = request.data.get('message')
        recipients = request.data.get('recipients')

        if not all([subject, html_message, recipients]):
            return Response(
                {"error": "All fields (subject, message, recipients) are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(recipients, list):
            return Response(
                {"error": "Recipients must be a list of email addresses"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Generate plain text version from HTML
            soup = BeautifulSoup(html_message, "html.parser")
            plain_message = soup.get_text(separator='\n').strip()

            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                html_message=html_message,
                fail_silently=False
            )
            
            return Response({
                "message": "Email sent successfully",
                "recipients": recipients
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "error": f"Failed to send email: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SetDecoyPasswordView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    
    @swagger_auto_schema(
        operation_description="Set a decoy password for your account",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['decoy_password'],
            properties={
                'decoy_password': openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={
            200: openapi.Response(
                description="Decoy password set successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: openapi.Response(
                description="Bad request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
        },
        tags=['User'],
    )
    def post(self, request):
        decoy_password = request.data.get('decoy_password')
        
        if not decoy_password:
            return Response(
                {"error": "Decoy password is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        request.user.profile.set_decoy_password(decoy_password)
        return Response({
            "message": "Decoy password set successfully"
        }, status=status.HTTP_200_OK)