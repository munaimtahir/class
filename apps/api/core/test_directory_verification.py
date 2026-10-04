import io
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from openpyxl import Workbook
from rest_framework.test import APIClient

from .models import DirectoryUser, UserRole

User = get_user_model()


def make_user(email: str, role: str = UserRole.OPERATOR):
    return User.objects.create_user(email=email, password="testpass123", role=role)


def make_directory_payload(start: int, count: int):
    payload = []
    for idx in range(start, start + count):
        payload.append(
            {
                "id": f"g-{idx}",
                "primaryEmail": f"user{idx}@school.edu",
                "name": {
                    "fullName": f"User {idx}",
                    "givenName": "User",
                    "familyName": str(idx),
                },
                "orgUnitPath": "/Students/Batch",
                "suspended": False,
                "archived": False,
            }
        )
    return payload


class DirectorySyncPaginationTests(TestCase):
    def setUp(self):
        self.user = make_user("operator@school.edu")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @patch("core.services.directory_module_service.GoogleDirectoryService.iter_user_pages")
    def test_sync_accumulates_pages_and_stats(self, iter_user_pages_mock):
        iter_user_pages_mock.return_value = [
            make_directory_payload(1, 500),
            make_directory_payload(501, 120),
        ]

        resp = self.client.post("/api/directory/sync", {}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["synced"], 620)
        self.assertEqual(resp.data["pages_fetched"], 2)
        self.assertEqual(resp.data["total_directory_users"], 620)
        self.assertEqual(DirectoryUser.objects.count(), 620)

        stats = self.client.get("/api/directory/stats")
        self.assertEqual(stats.status_code, 200)
        self.assertEqual(stats.data["total_directory_users"], 620)
        self.assertIsNotNone(stats.data["latest_sync_job"])
        self.assertEqual(stats.data["latest_sync_job"]["users_fetched_total"], 620)

        users = self.client.get("/api/directory/users")
        self.assertEqual(users.status_code, 200)
        self.assertEqual(len(users.data), 620)


class DirectoryVerificationApiTests(TestCase):
    def setUp(self):
        self.user = make_user("operator2@school.edu")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

        DirectoryUser.objects.create(
            google_user_id="g-a",
            primary_email="alice.brown@school.edu",
            full_name="Alice Brown",
            normalized_email="alice.brown@school.edu",
            normalized_full_name="alice brown",
            normalized_phone="5551112222",
            aliases_json=["alice.alt@school.edu"],
            phones_json=["5551112222"],
            roll_number="1001",
        )
        DirectoryUser.objects.create(
            google_user_id="g-j1",
            primary_email="john.one@school.edu",
            full_name="John Doe",
            normalized_email="john.one@school.edu",
            normalized_full_name="john doe",
            normalized_phone="5553331111",
        )
        DirectoryUser.objects.create(
            google_user_id="g-j2",
            primary_email="john.two@school.edu",
            full_name="John Doe",
            normalized_email="john.two@school.edu",
            normalized_full_name="john doe",
            normalized_phone="5553332222",
        )

    def _csv_file(self):
        data = (
            "Name,Roll No,Email Address,Phone Number,Official Email Issued,Email PMC\n"
            "Alice Brown,1001,,,alice.brown@school.edu,\n"
            "Alias Match,,, ,alice.alt@school.edu,\n"
            "Unknown User,9001,unknown@example.com,,,\n"
            "John Doe,,,,,\n"
            ",1234,,,,\n"
        )
        return SimpleUploadedFile("verify.csv", data.encode("utf-8"), content_type="text/csv")

    def _xlsx_file(self):
        wb = Workbook()
        ws = wb.active
        ws.title = "Users"
        ws.append(["Name", "Roll No", "Email Address", "Phone Number", "Official Email Issued", "Email PMC"])
        ws.append(["Alice Brown", "1001", "", "", "alice.brown@school.edu", ""])
        stream = io.BytesIO()
        wb.save(stream)
        stream.seek(0)
        return SimpleUploadedFile(
            "verify.xlsx",
            stream.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_csv_upload_mapping_and_verdicts(self):
        analyze = self.client.post("/api/directory/verify-upload", {"file": self._csv_file()})
        self.assertEqual(analyze.status_code, 200)
        self.assertTrue(analyze.data["requires_mapping"])
        mapping = analyze.data["suggested_mapping"]

        run = self.client.post(
            "/api/directory/verify-upload",
            {"file": self._csv_file(), "mapping": json.dumps(mapping)},
        )
        self.assertEqual(run.status_code, 201)
        self.assertEqual(run.data["status"], "completed")
        self.assertEqual(run.data["summary_json"]["exists"], 2)
        self.assertEqual(run.data["summary_json"]["does_not_exist"], 1)
        self.assertEqual(run.data["summary_json"]["ambiguous"], 1)
        self.assertEqual(run.data["summary_json"]["invalid_input"], 1)

        job_id = run.data["id"]
        rows = self.client.get(f"/api/directory/verify-jobs/{job_id}/rows")
        self.assertEqual(rows.status_code, 200)
        verdicts = [r["verdict"] for r in rows.data["results"]]
        self.assertIn("exists", verdicts)
        self.assertIn("does_not_exist", verdicts)
        self.assertIn("ambiguous", verdicts)
        self.assertIn("invalid_input", verdicts)

    def test_xlsx_upload_and_export(self):
        analyze = self.client.post("/api/directory/verify-upload", {"file": self._xlsx_file()})
        self.assertEqual(analyze.status_code, 200)
        self.assertTrue(analyze.data["requires_mapping"])

        run = self.client.post(
            "/api/directory/verify-upload",
            {
                "file": self._xlsx_file(),
                "mapping": json.dumps(analyze.data["suggested_mapping"]),
                "sheet_name": "Users",
            },
        )
        self.assertEqual(run.status_code, 201)
        self.assertIn("id", run.data)
        jobs = self.client.get("/api/directory/verify-jobs")
        self.assertEqual(jobs.status_code, 200)
        self.assertGreaterEqual(len(jobs.data), 1)
        job_id = jobs.data[0]["id"]

        csv_export = self.client.get(f"/api/directory/verify-jobs/{job_id}/export?file_format=csv")
        self.assertEqual(csv_export.status_code, 200, csv_export.content.decode("utf-8"))
        self.assertIn("text/csv", csv_export["Content-Type"])
        self.assertIn("row_no", csv_export.content.decode("utf-8"))

        xlsx_export = self.client.get(f"/api/directory/verify-jobs/{job_id}/export?file_format=xlsx")
        self.assertEqual(xlsx_export.status_code, 200)
        self.assertIn(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            xlsx_export["Content-Type"],
        )

    def test_verify_upload_rejects_insufficient_mapping(self):
        resp = self.client.post(
            "/api/directory/verify-upload",
            {
                "file": self._csv_file(),
                "mapping": json.dumps(
                    {
                        "name": "",
                        "roll_no": "Roll No",
                        "email_address": "",
                        "phone_number": "",
                        "official_email_issued": "",
                        "email_pmc": "",
                    }
                ),
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["code"], "insufficient_mapping")
