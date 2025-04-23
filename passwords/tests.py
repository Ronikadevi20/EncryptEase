from django.test import TestCase

# Create your tests here.
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Password, SharedPassword
import uuid
from unittest.mock import patch
User = get_user_model()

class PasswordVaultTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="pass1234")
        self.other_user = User.objects.create_user(username="hacker", email="hacker@example.com", password="pass456")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_password_with_category(self):
        data = {
            "name": "Netflix",
            "username": "netflixuser",
            "password_value": "mypass123",
            "website_url": "https://www.netflix.com",
            "notes": "My streaming password"
        }
        response = self.client.post("/api/passwords/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("category", response.data)
        self.assertEqual(response.data["category"], "ENTERTAINMENT")

    def test_password_list_filters_deleted(self):
        Password.objects.create(user=self.user, name="Active", password_value="a")
        deleted = Password.objects.create(user=self.user, name="Deleted", password_value="b", is_deleted=True)
        response = self.client.get("/api/passwords/")
        names = [p["name"] for p in response.data]
        self.assertIn("Active", names)
        self.assertNotIn("Deleted", names)

    def test_update_password(self):
        password = Password.objects.create(user=self.user, name="Old", password_value="123")
        response = self.client.put(f"/api/passwords/{password.id}/", {
            "name": "Updated",
            "username": "me",
            "password_value": "newpass",
            "website_url": "",
            "notes": "Updated notes"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Updated")

    def test_soft_delete_password(self):
        password = Password.objects.create(user=self.user, name="To Delete", password_value="abc")
        response = self.client.delete(f"/api/passwords/{password.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        password.refresh_from_db()
        self.assertTrue(password.is_deleted)
        self.assertIsNotNone(password.deleted_at)
    def test_missing_required_field(self):
        response = self.client.post("/api/passwords/", {
            "username": "abc"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)
        self.assertIn("password_value", response.data)
    def test_create_password_with_long_inputs(self):
        long_name = "A" * 255
        long_username = "U" * 255
        long_password = "P" * 500
        long_notes = "Note" * 1000  # 4000+ chars

        response = self.client.post("/api/passwords/", {
            "name": long_name,
            "username": long_username,
            "password_value": long_password,
            "website_url": "https://example.com",
            "notes": long_notes
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], long_name)

    @patch("passwords.serializers.pipeline")
    def test_ai_classification_fallback(self, mock_pipeline):
        mock_pipeline.side_effect = Exception("Model load failed")

        response = self.client.post("/api/passwords/", {
            "name": "TestFail",
            "username": "test",
            "password_value": "failpass",
            "website_url": "https://fail.com",
            "notes": "Testing fallback"
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["category"], "OTHER")

    def test_create_password_without_website_url(self):
        response = self.client.post("/api/passwords/", {
            "name": "Test No URL",
            "username": "nouser",
            "password_value": "SuperSecure123!",
            "notes": "Just testing AI without URL"
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("category", response.data)
        
    def test_create_password_with_invalid_website_url(self):
        response = self.client.post("/api/passwords/", {
            "name": "Invalid URL",
            "username": "test",
            "password_value": "Test123!",
            "website_url": "https://abcxyz.unknown",
            "notes": "Test with unrecognized domain"
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(response.data["category"], [
            "SOCIAL", "EMAIL", "FINANCE", "WORK", "ENTERTAINMENT", "SHOPPING", "OTHER"
        ])

    def test_weak_password_with_special_characters_only(self):
        response = self.client.post("/api/passwords/", {
        "name": "Symbols",
        "username": "user",
        "password_value": "@#$%^&*!",
        "website_url": "https://test.com",
        "notes": "Special chars only"
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)