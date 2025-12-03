from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework.test import APIRequestFactory, force_authenticate

import smtplib
import socket
from django.core.mail import BadHeaderError

from apps.notifications.api.api import EmailAPIView

User = get_user_model()


class EmailAPIViewTests(TestCase):

    def setUp(self):
        from apps.users.models import Ideal
        from Nutrimate.core.enums import Goal
        
        self.factory = APIRequestFactory()
        # Ensure from email is set so sending logic doesn't fail by default
        settings.DEFAULT_FROM_EMAIL = "noreply@test.com"

        # admin ideal
        admin_ideal = Ideal.objects.create(goal=Goal.NUTRITION)
        # custom User model requires several required fields, so use create_user
        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="pass",
            first_name="Admin",
            last_name="User",
            age=30,
            height=170.0,
            weight=70.0,
            is_staff=True,
            is_superuser=True,
            ideal=admin_ideal,
        )

    def make_user(self, email, email_opt_out=False):
        """Helper to create a valid user for tests using required fields."""
        # create a minimal Ideal for the user (User.ideal is non-nullable)
        from apps.users.models import Ideal
        from Nutrimate.core.enums import Goal

        ideal = Ideal.objects.create(goal=Goal.NUTRITION)

        return User.objects.create_user(
            email=email,
            password="pass",
            first_name="Test",
            last_name="User",
            age=25,
            height=170.0,
            weight=70.0,
            email_opt_out=email_opt_out,
            ideal=ideal,
        )

    # ---------- TEST CASES ----------

    def test_requires_admin_permission(self):
        request = self.factory.post("/email/?template=reminder")
        view = EmailAPIView.as_view()

        response = view(request)
        # DRF may use 401 or 403 depending on auth config
        self.assertIn(response.status_code, [401, 403])

    def test_invalid_template_returns_400(self):
        request = self.factory.post("/email/?template=no_existe")
        force_authenticate(request, user=self.admin)
        view = EmailAPIView.as_view()

        response = view(request)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "Template no permitida.")

    def test_missing_from_email_returns_500(self):
        settings.DEFAULT_FROM_EMAIL = None
        settings.SERVER_EMAIL = None

        request = self.factory.post("/email/?template=reminder")
        force_authenticate(request, user=self.admin)
        view = EmailAPIView.as_view()

        response = view(request)
        self.assertEqual(response.status_code, 500)
        self.assertIn("Server email not configured", response.data["detail"])

    def test_no_users_available_returns_count_zero(self):
        request = self.factory.post("/email/?template=reminder")
        force_authenticate(request, self.admin)

        with patch("apps.notifications.api.api.User.objects.filter") as mock_filter:
            mock_qs = MagicMock()
            mock_qs.exists.return_value = False
            mock_filter.return_value = mock_qs

            view = EmailAPIView.as_view()
            response = view(request)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["count"], 0)

    def test_progress_template_applies_filter_function(self):
        # Define 2 users with progress; 1 without
        user1 = self.make_user("u1@test.com", email_opt_out=False)
        user2 = self.make_user("u2@test.com", email_opt_out=False)
        user3 = self.make_user("u3@test.com", email_opt_out=False)

        request = self.factory.post("/email/?template=progress_reminder")
        force_authenticate(request, self.admin)

           # Mock queryset + ensure API uses our mock filter_func by overriding
           # the TEMPLATE_CONFIG entry inside the API module (it holds a reference
           # to the function at import-time).
        import apps.notifications.api.api as api_mod

        with patch("apps.notifications.api.api.User.objects.filter") as mock_filter, \
            patch("apps.notifications.api.api.send_bulk_emails") as mock_send:

            mock_base_qs = MagicMock()
            mock_filtered_qs = MagicMock()

            mock_base_qs.exists.return_value = True
            mock_filtered_qs.exists.return_value = True

            # iterate over base to provide tuple (user, email) style if needed
            mock_base_qs.__iter__.return_value = [(user1, user1.email), (user2, user2.email)]
            mock_filter.return_value = mock_base_qs
            # Override the API module's TEMPLATE_CONFIG to use our mocked filter
            original_filter = api_mod.TEMPLATE_CONFIG['progress_reminder']['filter_func']
            api_mod.TEMPLATE_CONFIG['progress_reminder']['filter_func'] = lambda base: mock_filtered_qs

            mock_filtered_qs.__iter__.return_value = [user1, user2]
            mock_send.return_value = 2

            try:
                view = EmailAPIView.as_view()
                response = view(request)
            finally:
                # restore original reference to avoid leaking into other tests
                api_mod.TEMPLATE_CONFIG['progress_reminder']['filter_func'] = original_filter

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["count"], 2)
            # Ensure send_bulk_emails called with expected args
            mock_send.assert_called_once()
            called_args, called_kwargs = mock_send.call_args
            self.assertEqual(called_args[0], 'progress_reminder')
            # subject expected
            self.assertIn('Notificación', called_args[1])
            # from email
            self.assertEqual(called_args[2], settings.DEFAULT_FROM_EMAIL)
            # recipient_list should be list of (user, email) tuples matching filtered_qs
            recip = called_args[3]
            self.assertIsInstance(recip, list)
            self.assertEqual(recip, [(user1, user1.email), (user2, user2.email)])

    def test_successful_email_sending(self):
        user = self.make_user("test@test.com", email_opt_out=False)

        request = self.factory.post("/email/?template=reminder")
        force_authenticate(request, self.admin)

        with patch("apps.notifications.api.api.send_bulk_emails", return_value=1) as mock_send:
            view = EmailAPIView.as_view()
            response = view(request)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["count"], 1)
            mock_send.assert_called_once()
            # verify the send call had the expected arguments for a static template
            called_args, _ = mock_send.call_args
            self.assertEqual(called_args[0], 'reminder')
            self.assertIn('Notificación', called_args[1])
            self.assertEqual(called_args[2], settings.DEFAULT_FROM_EMAIL)
            # recipient_list should be a list of tuples (user, email)
            # by default the admin user (created in setUp) also does not opt-out,
            # so both admin and the new user will be in the recipients list
            self.assertEqual(called_args[3], [(self.admin, self.admin.email), (user, user.email)])

    def test_bad_header_error(self):
        user = self.make_user("test@test.com", email_opt_out=False)

        request = self.factory.post("/email/?template=reminder")
        force_authenticate(request, self.admin)

        with patch("apps.notifications.api.api.send_bulk_emails", side_effect=BadHeaderError):
            view = EmailAPIView.as_view()
            response = view(request)

            self.assertEqual(response.status_code, 400)

    def test_smtp_recipient_refused(self):
        user = self.make_user("test@test.com")

        request = self.factory.post("/email/?template=reminder")
        force_authenticate(request, self.admin)

        with patch("apps.notifications.api.api.send_bulk_emails",
                   side_effect=smtplib.SMTPRecipientsRefused(recipients="x")):
            view = EmailAPIView.as_view()
            response = view(request)

            self.assertEqual(response.status_code, 400)

    def test_smtp_auth_error(self):
        user = self.make_user("test@test.com")

        request = self.factory.post("/email/?template=reminder")
        force_authenticate(request, self.admin)

        with patch("apps.notifications.api.api.send_bulk_emails",
                   side_effect=smtplib.SMTPAuthenticationError(535, "Error")):
            view = EmailAPIView.as_view()
            response = view(request)

            self.assertEqual(response.status_code, 503)

    def test_smtp_general_error(self):
        user = self.make_user("test@test.com")

        request = self.factory.post("/email/?template=reminder")
        force_authenticate(request, self.admin)

        with patch("apps.notifications.api.api.send_bulk_emails",
                   side_effect=smtplib.SMTPException("boom")):
            view = EmailAPIView.as_view()
            response = view(request)

            self.assertEqual(response.status_code, 503)

    def test_network_error(self):
        user = self.make_user("test@test.com")

        request = self.factory.post("/email/?template=reminder")
        force_authenticate(request, self.admin)

        with patch("apps.notifications.api.api.send_bulk_emails",
                   side_effect=socket.gaierror("fail")):
            view = EmailAPIView.as_view()
            response = view(request)

            self.assertEqual(response.status_code, 503)

    def test_unexpected_exception(self):
        user = self.make_user("test@test.com")

        request = self.factory.post("/email/?template=reminder")
        force_authenticate(request, self.admin)

        with patch("apps.notifications.api.api.send_bulk_emails",
                   side_effect=Exception("random error")):
            view = EmailAPIView.as_view()
            response = view(request)

            self.assertEqual(response.status_code, 500)
