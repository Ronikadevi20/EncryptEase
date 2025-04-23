from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import UserProfile
import pyotp
from django.core import mail
from bs4 import BeautifulSoup
import json

class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'password2': 'testpass123'
        }
        self.login_data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }

    def test_user_registration(self):
        """Test user registration flow"""
        response = self.client.post('/api/auth/register', self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        
        # Check that the response contains the success message
        self.assertIn('message', response.data)
        
        # Check that an email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, '[EncryptEase] Successful Registration – Verify Your Email')
        
        # Check the user is created but not verified
        user = User.objects.first()
        self.assertFalse(user.profile.otp_verified)

    def test_user_registration_password_mismatch(self):
        """Test registration with mismatched passwords"""
        data = self.user_data.copy()
        data['password2'] = 'differentpass'
        response = self.client.post('/api/auth/register', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_user_login_without_verification(self):
        """Test login before email verification"""
        # Register user
        self.client.post('/api/auth/register', self.user_data)
        
        # Attempt login
        response = self.client.post('/api/auth/login', self.login_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'Email not verified. Please verify your email first.')


    def test_decoy_password_login(self):
        """Test login with decoy password"""
        # Register and verify user
        self.client.post('/api/auth/register', self.user_data)
        user = User.objects.get(email=self.user_data['email'])
        user.profile.otp_verified = True
        user.profile.set_decoy_password('decoypass123')
        user.profile.save()
        
        # Login with decoy password
        login_data = {
            'email': self.user_data['email'],
            'password': 'decoypass123'
        }
        response = self.client.post('/api/auth/login', login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['decoy'])
        
        # Check decoy login email was sent
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[1].subject, '[EncryptEase] Decoy Login Detected')
    
    def test_login_without_otp(self):
        """Test login with decoy password"""
        # Register and verify user
        self.client.post('/api/auth/register', self.user_data)
        user = User.objects.get(email=self.user_data['email'])
        user.profile.otp_verified = True
        user.profile.set_decoy_password('decoypass123')
        user.profile.save()
        
        # Login with decoy password
        login_data = {
            'email': self.user_data['email'],
            'password': 'decoypass123'
        }
        response = self.client.post('/api/auth/login', login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['decoy'])
        
        # Check decoy login email was sent
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[1].subject, '[EncryptEase] Decoy Login Detected')
    
    def test_password_update(self):
        """Test login before email verification"""
        # Register user
        self.client.post('/api/auth/register', self.user_data)
        
        # Attempt login
        response = self.client.post('/api/auth/login', self.login_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'Email not verified. Please verify your email first.')


class EmailServiceTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_send_email(self):
        """Test the email sending endpoint"""
        email_data = {
            'subject': 'Test Email',
            'message': '<html><body><h1>Test</h1><p>This is a test email</p></body></html>',
            'recipients': ['test1@example.com', 'test2@example.com']
        }
        
        response = self.client.post(
            '/api/auth/send-email',
            data=json.dumps(email_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Test Email')
        self.assertEqual(mail.outbox[0].to, ['test1@example.com', 'test2@example.com'])
        
        # Check HTML content
        self.assertIn('<h1>Test</h1>', mail.outbox[0].alternatives[0][0])
        
        # Check plain text version was generated
        soup = BeautifulSoup(email_data['message'], "html.parser")
        plain_text = soup.get_text(separator='\n').strip()
        self.assertIn(plain_text, mail.outbox[0].body)

    def test_send_email_invalid_data(self):
        """Test email sending with invalid data"""
        # Missing subject
        response = self.client.post('/api/auth/send-email', {
            'message': '<html><body>Test</body></html>',
            'recipients': ['test@example.com']
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)