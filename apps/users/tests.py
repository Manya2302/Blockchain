from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.evidence.forms import EvidenceUploadForm
from apps.users.forms import RegisterForm


@override_settings(SECURE_SSL_REDIRECT=False)
class SecurityRegressionTests(TestCase):
    def test_register_form_excludes_admin_role(self):
        form = RegisterForm()
        roles = [value for value, _label in form.fields["role"].choices]
        self.assertIn("SUBMITTER", roles)
        self.assertIn("ANALYST", roles)
        self.assertNotIn("ADMIN", roles)

    def test_dashboard_requires_authentication(self):
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login/", response["Location"])

    def test_mobile_api_requires_bearer_token(self):
        response = self.client.get("/api/mobile/evidence/")
        self.assertEqual(response.status_code, 401)

    def test_custom_404_does_not_expose_django_route_list(self):
        response = self.client.get("/definitely-not-a-real-page/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "outside the vault", status_code=404)
        self.assertNotContains(response, "Using the URLconf", status_code=404)

    def test_evidence_upload_rejects_disallowed_extension(self):
        user = User.objects.create_user(username="submitter", password="StrongPass123!")
        upload = SimpleUploadedFile(
            "payload.exe",
            b"MZ fake executable",
            content_type="application/x-msdownload",
        )
        form = EvidenceUploadForm(
            data={"title": "Suspicious executable", "description": "", "case_id": "", "tags": ""},
            files={"file": upload},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("file", form.errors)
