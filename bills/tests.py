from django.test import TestCase

# Create your tests here.
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Bill
import io
from datetime import date, timedelta

User = get_user_model()

class BillTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ronika", email="ronika@test.com", password="pass1234")
        self.other_user = User.objects.create_user(username="notme", email="notme@test.com", password="pass5678")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.default_data = {
            "name": "Internet",
            "amount": "50.00",
            "due_date": (date.today() + timedelta(days=5)).isoformat(),
            "category": "UTILITIES"
        }

    def test_create_bill_valid(self):
        response = self.client.post("/api/bills/", self.default_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Bill.objects.count(), 1)
        self.assertEqual(Bill.objects.first().user, self.user)

    def test_create_bill_invalid_amount(self):
        data = self.default_data.copy()
        data["amount"] = "-10.00"
        response = self.client.post("/api/bills/", data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("amount", response.data)

    def test_create_bill_missing_required_fields(self):
        response = self.client.post("/api/bills/", {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)
        self.assertIn("amount", response.data)
        self.assertIn("due_date", response.data)

    def test_read_bills_only_user_and_not_deleted(self):
        Bill.objects.create(user=self.user, name="Active Bill", amount=20, due_date=date.today())
        Bill.objects.create(user=self.user, name="Deleted Bill", amount=25, due_date=date.today(), is_deleted=True)
        Bill.objects.create(user=self.other_user, name="Other User", amount=30, due_date=date.today())

        response = self.client.get("/api/bills/")
        names = [bill["name"] for bill in response.data]
        self.assertIn("Active Bill", names)
        self.assertNotIn("Deleted Bill", names)
        self.assertNotIn("Other User", names)

    def test_update_bill_fields(self):
        bill = Bill.objects.create(user=self.user, name="Old Name", amount=30, due_date=date.today())
        response = self.client.put(f"/api/bills/{bill.id}/", {
            "name": "New Name",
            "amount": "60.00",
            "due_date": (date.today() + timedelta(days=10)).isoformat()
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        bill.refresh_from_db()
        self.assertEqual(bill.name, "New Name")
        self.assertEqual(str(bill.amount), "60.00")

    def test_soft_delete_bill(self):
        bill = Bill.objects.create(user=self.user, name="Delete Me", amount=15, due_date=date.today())
        response = self.client.post(f"/api/bills/{bill.id}/soft_delete/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        bill.refresh_from_db()
        self.assertTrue(bill.is_deleted)

    def test_restore_deleted_bill(self):
        bill = Bill.objects.create(user=self.user, name="To Restore", amount=30, due_date=timezone.now().date(), is_deleted=True)
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(f"/api/bills/{bill.id}/restore/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        bill.refresh_from_db()
        self.assertFalse(bill.is_deleted)

    def test_destroy_bill_overrides_to_soft_delete(self):
        bill = Bill.objects.create(user=self.user, name="Soft Kill", amount=20, due_date=date.today())
        response = self.client.delete(f"/api/bills/{bill.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        bill.refresh_from_db()
        self.assertTrue(bill.is_deleted)

    def test_payment_status_updates(self):
        bill = Bill.objects.create(user=self.user, name="Payable", amount=99, due_date=date.today(), is_paid=False)
        response = self.client.put(f"/api/bills/{bill.id}/", {
            "name": bill.name,
            "amount": "99.00",
            "due_date": bill.due_date.isoformat(),
            "is_paid": True,
            "payment_date": date.today().isoformat()
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        bill.refresh_from_db()
        self.assertTrue(bill.is_paid)
        self.assertIsNotNone(bill.payment_date)
        
    def test_upload_receipt_and_remove_it_on_update(self):
        file = SimpleUploadedFile("receipt.pdf", b"dummy file content", content_type="application/pdf")
        bill = Bill.objects.create(user=self.user, name="With Receipt", amount=15, due_date=date.today(), receipt=file)

        # Confirm file exists
        self.assertTrue(bill.receipt)

        # Update: remove the file
        response = self.client.put(
            f"/api/bills/{bill.id}/",
            {
                "name": "With Receipt",
                "amount": "15.00",
                "due_date": bill.due_date.isoformat(),
                "receipt": '',  # ← THIS is the key part
            },
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        bill.refresh_from_db()
        self.assertFalse(bill.receipt)
