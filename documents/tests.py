from django.test import TestCase

# Create your tests here.

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import timedelta
from .models import Document
import io

User = get_user_model()

class DocumentTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ronika", email="ronika@test.com", password="pass1234")
        self.other_user = User.objects.create_user(username="notme", email="notme@test.com", password="pass5678")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.valid_file = SimpleUploadedFile("testdoc.pdf", b"dummy content", content_type="application/pdf")
        self.future_date = timezone.now() + timedelta(days=10)

    def test_upload_document(self):
        response = self.client.post("/api/documents/", {
            "title": "My File",
            "description": "Test PDF",
            "file": self.valid_file,
            "expiry_date": self.future_date
        }, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        doc = Document.objects.get()
        self.assertEqual(doc.user, self.user)
        self.assertEqual(doc.file_type, "PDF")
        self.assertGreater(doc.file_size, 0)

    def test_upload_invalid_file_extension(self):
        invalid_file = SimpleUploadedFile("malware.exe", b"bad!", content_type="application/octet-stream")
        response = self.client.post("/api/documents/", {
            "title": "Bad File",
            "file": invalid_file
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_document_metadata(self):
        doc = Document.objects.create(user=self.user, title="Old", file=self.valid_file, file_type="PDF", file_size=100)
        response = self.client.patch(f"/api/documents/{doc.id}/", {
            "title": "New Title",
            "description": "Updated"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        doc.refresh_from_db()
        self.assertEqual(doc.title, "New Title")

    def test_soft_delete_document(self):
        doc = Document.objects.create(user=self.user, title="To Delete", file=self.valid_file, file_type="PDF", file_size=50)
        response = self.client.delete(f"/api/documents/{doc.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        doc.refresh_from_db()
        self.assertTrue(doc.is_deleted)

    def test_download_active_document(self):
        doc = Document.objects.create(user=self.user, title="Downloadable", file=self.valid_file, file_type="PDF", file_size=100)
        response = self.client.get(f"/api/documents/{doc.id}/download/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("attachment", response.get("Content-Disposition", ""))

    def test_download_expired_document_blocked(self):
        past_date = timezone.now() - timedelta(days=2)
        doc = Document.objects.create(user=self.user, title="Expired", file=self.valid_file, file_type="PDF", file_size=100, expiry_date=past_date)
        response = self.client.get(f"/api/documents/{doc.id}/download/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_expiry_status(self):
        Document.objects.create(user=self.user, title="Active", file=self.valid_file, file_type="PDF", file_size=10, expiry_date=self.future_date)
        Document.objects.create(user=self.user, title="Expired", file=self.valid_file, file_type="PDF", file_size=10, expiry_date=timezone.now() - timedelta(days=1))

        # Active
        resp_active = self.client.get("/api/documents/?expiry_status=active")
        self.assertEqual(resp_active.status_code, status.HTTP_200_OK)
        self.assertTrue(any("Active" in doc["title"] for doc in resp_active.data))

        # Expired
        resp_expired = self.client.get("/api/documents/?expiry_status=expired")
        self.assertEqual(resp_expired.status_code, status.HTTP_200_OK)
        self.assertTrue(any("Expired" in doc["title"] for doc in resp_expired.data))

    def test_expiry_date_validation(self):
        past_date = timezone.now() - timedelta(days=5)
        response = self.client.post("/api/documents/", {
            "title": "Old Doc",
            "file": self.valid_file,
            "expiry_date": past_date
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expiry_date", response.data)

    def test_document_stats(self):
        Document.objects.create(user=self.user, title="One", file=self.valid_file, file_type="PDF", file_size=1)
        Document.objects.create(user=self.user, title="Two", file=self.valid_file, file_type="PDF", file_size=1, expiry_date=timezone.now() - timedelta(days=1))
        Document.objects.create(user=self.user, title="Soon", file=self.valid_file, file_type="PDF", file_size=1, expiry_date=timezone.now() + timedelta(days=3))

        response = self.client.get("/api/documents/stats/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total_documents", response.data)
        self.assertEqual(response.data["total_documents"], 3)
        self.assertEqual(response.data["expired_documents"], 1)
        self.assertEqual(response.data["expiring_soon"], 1)