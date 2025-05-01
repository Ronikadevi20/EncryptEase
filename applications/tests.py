from django.test import TestCase

# Create your tests here.
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from .models import JobApplication, FollowUpDraft, Resume, CoverLetter
from .models import Resume, CoverLetter, InterviewPrepDraft, InterviewPrepNote

User = get_user_model()

class ApplicationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ronika", email="ronika@test.com", password="pass1234")
        self.other_user = User.objects.create_user(username="notme", email="notme@test.com", password="pass5678")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_job_application_valid(self):
        data = {
            "job_title": "Software Engineer",
            "company": "OpenAI",
            "location": "Remote",
            "status": "applied",
        }
        response = self.client.post("/api/applications/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(JobApplication.objects.count(), 1)

    def test_create_job_requires_deadline_for_interview_status(self):
        data = {
            "job_title": "Dev Intern",
            "company": "Example Ltd",
            "status": "interviewing",
        }
        response = self.client.post("/api/applications/", data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("deadline_date", response.data)

    def test_create_job_invalid_deadline_with_applied_status(self):
        data = {
            "job_title": "Marketing",
            "company": "Company",
            "status": "applied",
            "deadline_date": (timezone.now() + timedelta(days=10)).date()
        }
        response = self.client.post("/api/applications/", data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_job_application(self):
        job = JobApplication.objects.create(user=self.user, job_title="Old", company="A")
        response = self.client.patch(f"/api/applications/{job.id}/", {"job_title": "Updated"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["job_title"], "Updated")

    def test_create_job_missing_required_fields(self):
        response = self.client.post("/api/applications/", {
            "company": "No Job Title"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("job_title", response.data)

    def test_update_requires_deadline_if_status_becomes_interview(self):
        job = JobApplication.objects.create(user=self.user, job_title="Status Check", company="HR", status="applied")
        response = self.client.patch(f"/api/applications/{job.id}/", {
            "status": "interviewing"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("deadline_date", response.data)

    def test_list_applications_for_user(self):
        JobApplication.objects.create(user=self.user, job_title="Mine", company="A")
        JobApplication.objects.create(user=self.other_user, job_title="Not Mine", company="B")
        response = self.client.get("/api/applications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['job_title'], "Mine")

    def test_access_control_patch_other_user(self):
        job = JobApplication.objects.create(user=self.user, job_title="Private", company="X")
        self.client.force_authenticate(user=self.other_user)
        response = self.client.patch(f"/api/applications/{job.id}/", {
            "job_title": "Hack!"
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_access_control_delete_other_user(self):
        job = JobApplication.objects.create(user=self.user, job_title="BlockMe", company="X")
        self.client.force_authenticate(user=self.other_user)
        response = self.client.delete(f"/api/applications/{job.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_soft_delete_application(self):
        job = JobApplication.objects.create(user=self.user, job_title="DeleteMe", company="Soft Inc")
        response = self.client.delete(f"/api/applications/{job.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        job.refresh_from_db()
        self.assertTrue(job.is_deleted)

    def test_deadline_is_required_only_for_specific_statuses(self):
        job = JobApplication.objects.create(user=self.user, job_title="Marketing", company="X", status="applied")
        response = self.client.patch(f"/api/applications/{job.id}/", {
            "deadline_date": timezone.now().date()
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    def test_create_resume(self):
            data = {
                "title": "Backend Resume",
                "job_title": "Backend Dev",
                "job_description": "Building APIs"
            }
            res = self.client.post("/api/applications/generate-resume/", data)
            self.assertEqual(res.status_code, status.HTTP_201_CREATED)
            self.assertEqual(Resume.objects.count(), 1)
            
    def test_create_cover_letter(self):
        data = {
            "title": "AI Role Cover",
            "job_title": "AI Engineer",
            "company": "DeepTech",
            "job_description": "Exciting AI work"
        }
        res = self.client.post("/api/applications/generate-cover-letter/", data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CoverLetter.objects.count(), 1)

    def test_access_control_on_resume(self):
        resume = Resume.objects.create(user=self.user, title="Secret", job_title="Hidden", job_description="Stuff")
        self.client.force_authenticate(user=self.other_user)
        res = self.client.get(f"/api/applications/generate-resumes/{resume.id}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
