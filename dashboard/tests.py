from datetime import date, time, timedelta
from django.test import TestCase
from django.contrib.auth.models import User

from clients.models import Owner, Dog
from scheduling.models import TrainingSession, Booking, PendingBookingRequest


class DashboardHomeViewTest(TestCase):
    """Testy panelu glownego (akcyjny widok)."""

    def setUp(self):
        self.user = User.objects.create_user(username="trener", password="testpass123")
        self.client.login(username="trener", password="testpass123")
        self.owner = Owner.objects.create(first_name="Ola", last_name="Testowa", phone="600111222")
        self.dog = Dog.objects.create(name="Pixel", owner=self.owner)

    def test_anonymous_redirected_to_login(self):
        self.client.logout()
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)

    def test_login_redirects_to_dashboard(self):
        self.client.logout()
        response = self.client.post("/login/", {"username": "trener", "password": "testpass123"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/dashboard/")

    def test_dashboard_accessible_when_logged_in(self):
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)

    def test_dashboard_shows_session_within_7_days(self):
        TrainingSession.objects.create(
            title="Bliski trening", date=date.today() + timedelta(days=3),
            start_time=time(10, 0), end_time=time(11, 0), capacity=1,
        )
        response = self.client.get("/dashboard/")
        self.assertContains(response, "Bliski trening")

    def test_dashboard_hides_session_beyond_7_days(self):
        TrainingSession.objects.create(
            title="Daleki trening", date=date.today() + timedelta(days=15),
            start_time=time(10, 0), end_time=time(11, 0), capacity=1,
        )
        response = self.client.get("/dashboard/")
        self.assertNotContains(response, "Daleki trening")

    def test_dashboard_hides_cancelled_sessions(self):
        TrainingSession.objects.create(
            title="Odwolany trening", date=date.today() + timedelta(days=1),
            start_time=time(10, 0), end_time=time(11, 0), capacity=1,
            status=TrainingSession.STATUS_CANCELLED,
        )
        response = self.client.get("/dashboard/")
        self.assertNotContains(response, "Odwolany trening")

    def test_dashboard_shows_pending_requests_count(self):
        session = TrainingSession.objects.create(
            date=date.today() + timedelta(days=1), start_time=time(10, 0), end_time=time(11, 0),
            capacity=1, is_public=True,
        )
        PendingBookingRequest.objects.create(
            session=session, submitted_name="Jan Nowak", submitted_phone="600999888",
            dog_name="Burek", rodo_consent=True,
        )
        response = self.client.get("/dashboard/")
        self.assertContains(response, "Jan Nowak")
        self.assertContains(response, "Wnioski czekajace na weryfikacje (1)")

    def test_dashboard_hides_pending_section_when_empty(self):
        response = self.client.get("/dashboard/")
        self.assertNotContains(response, "Wnioski czekajace na weryfikacje")

    def test_dashboard_shows_recently_added_owner(self):
        response = self.client.get("/dashboard/")
        self.assertContains(response, "Ola Testowa")

    def test_dashboard_has_quick_action_links(self):
        response = self.client.get("/dashboard/")
        self.assertContains(response, 'href="/clients/add/"')
        self.assertContains(response, 'href="/dogs/add/"')
        self.assertContains(response, 'href="/scheduling/sessions/add/"')
        self.assertContains(response, 'href="/exercises/add/"')
