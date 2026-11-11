from datetime import date, time, timedelta
from django.test import TestCase
from django.contrib.auth.models import User
from clients.models import Owner, Dog
from .models import TrainingSession, Booking, PendingBookingRequest


class TrainingSessionModelTest(TestCase):
    def setUp(self):
        self.session = TrainingSession.objects.create(
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0), end_time=time(11, 0), capacity=2,
        )
        self.owner = Owner.objects.create(first_name="Ola", last_name="Test", phone="600111222")
        self.dog1 = Dog.objects.create(name="Pixel", owner=self.owner)
        self.dog2 = Dog.objects.create(name="Reksio", owner=self.owner)

    def test_str_format(self):
        self.assertIn("10:00", str(self.session))

    def test_available_slots_full_capacity(self):
        self.assertEqual(self.session.available_slots(), 2)

    def test_available_slots_decreases_with_confirmed_booking(self):
        Booking.objects.create(session=self.session, dog=self.dog1, status=Booking.STATUS_CONFIRMED)
        self.assertEqual(self.session.available_slots(), 1)

    def test_is_full_false_when_space_available(self):
        Booking.objects.create(session=self.session, dog=self.dog1, status=Booking.STATUS_CONFIRMED)
        self.assertFalse(self.session.is_full())

    def test_is_full_true_at_capacity(self):
        Booking.objects.create(session=self.session, dog=self.dog1, status=Booking.STATUS_CONFIRMED)
        Booking.objects.create(session=self.session, dog=self.dog2, status=Booking.STATUS_CONFIRMED)
        self.assertTrue(self.session.is_full())

    def test_waiting_list_not_counted_in_confirmed(self):
        Booking.objects.create(session=self.session, dog=self.dog1, status=Booking.STATUS_WAITING_LIST)
        self.assertEqual(self.session.confirmed_count(), 0)
        self.assertFalse(self.session.is_full())

    def test_get_conflicting_sessions_detects_overlap(self):
        other = TrainingSession.objects.create(
            date=self.session.date, start_time=time(10, 30), end_time=time(11, 30), capacity=1,
        )
        conflicts = self.session.get_conflicting_sessions()
        self.assertIn(other, conflicts)

    def test_get_conflicting_sessions_no_overlap(self):
        TrainingSession.objects.create(
            date=self.session.date, start_time=time(12, 0), end_time=time(13, 0), capacity=1,
        )
        self.assertEqual(self.session.get_conflicting_sessions(), [])

    def test_get_conflicting_sessions_ignores_cancelled(self):
        cancelled = TrainingSession.objects.create(
            date=self.session.date, start_time=time(10, 30), end_time=time(11, 30), capacity=1,
            status=TrainingSession.STATUS_CANCELLED,
        )
        conflicts = self.session.get_conflicting_sessions()
        self.assertNotIn(cancelled, conflicts)

    def test_duplicate_next_week_shifts_date_by_7_days(self):
        new_session = self.session.duplicate_next_week()
        self.assertEqual(new_session.date, self.session.date + timedelta(days=7))
        self.assertEqual(new_session.start_time, self.session.start_time)
        self.assertEqual(new_session.capacity, self.session.capacity)

    def test_duplicate_next_week_does_not_copy_bookings(self):
        Booking.objects.create(session=self.session, dog=self.dog1, status=Booking.STATUS_CONFIRMED)
        new_session = self.session.duplicate_next_week()
        self.assertEqual(new_session.bookings.count(), 0)

    def test_cancel_cascades_to_active_bookings(self):
        b1 = Booking.objects.create(session=self.session, dog=self.dog1, status=Booking.STATUS_CONFIRMED)
        b2 = Booking.objects.create(session=self.session, dog=self.dog2, status=Booking.STATUS_WAITING_LIST)
        self.session.cancel()
        b1.refresh_from_db()
        b2.refresh_from_db()
        self.assertEqual(self.session.status, TrainingSession.STATUS_CANCELLED)
        self.assertEqual(b1.status, Booking.STATUS_CANCELLED)
        self.assertEqual(b2.status, Booking.STATUS_CANCELLED)


class BookingModelTest(TestCase):
    def setUp(self):
        self.session = TrainingSession.objects.create(
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0), end_time=time(11, 0), capacity=1,
        )
        self.owner = Owner.objects.create(first_name="Ola", last_name="Test", phone="600111222")
        self.dog1 = Dog.objects.create(name="Pixel", owner=self.owner)
        self.dog2 = Dog.objects.create(name="Reksio", owner=self.owner)

    def test_promote_from_waiting_list_fifo_order(self):
        """Dwie osoby na liscie rezerwowej - po zwolnieniu miejsca
        awansowana MUSI byc ta ktora czeka dluzej (FIFO wg created_at)."""
        dog3 = Dog.objects.create(name="Trzeci", owner=self.owner)
        confirmed = Booking.objects.create(session=self.session, dog=self.dog1, status=Booking.STATUS_CONFIRMED)
        waiting1 = Booking.objects.create(session=self.session, dog=self.dog2, status=Booking.STATUS_WAITING_LIST)
        waiting2 = Booking.objects.create(session=self.session, dog=dog3, status=Booking.STATUS_WAITING_LIST)

        confirmed.status = Booking.STATUS_CANCELLED
        confirmed.save()
        promoted = confirmed.promote_from_waiting_list_if_needed()

        self.assertEqual(promoted, waiting1)
        waiting1.refresh_from_db()
        waiting2.refresh_from_db()
        self.assertEqual(waiting1.status, Booking.STATUS_CONFIRMED)
        self.assertEqual(waiting2.status, Booking.STATUS_WAITING_LIST)

    def test_promote_returns_none_when_no_waiting_list(self):
        booking = Booking.objects.create(session=self.session, dog=self.dog1, status=Booking.STATUS_CONFIRMED)
        booking.status = Booking.STATUS_CANCELLED
        booking.save()
        self.assertIsNone(booking.promote_from_waiting_list_if_needed())

    def test_promote_returns_none_when_session_still_full(self):
        """Jesli sesja ma capacity=2 i jedna osoba sie odwolala, ale
        wciaz jest inna osoba confirmed - nie powinno sie nic dziac
        (brak wolnego miejsca po odliczeniu)."""
        self.session.capacity = 1
        self.session.save()
        b1 = Booking.objects.create(session=self.session, dog=self.dog1, status=Booking.STATUS_CONFIRMED)
        waiting = Booking.objects.create(session=self.session, dog=self.dog2, status=Booking.STATUS_WAITING_LIST)
        # symulujemy ze miejsce NIE zostalo zwolnione (status sie nie zmienil)
        promoted = b1.promote_from_waiting_list_if_needed()
        self.assertIsNone(promoted)  # bo is_full() wciaz True (b1 nadal confirmed)


class BookingViewsTest(TestCase):
    """Testy integracyjne widokow - weryfikuja kluczowa logike biznesowa
    (deduplikacja klienta, lista rezerwowa, walidacja podwojnego zapisu)."""

    def setUp(self):
        self.user = User.objects.create_user(username="trener", password="testpass123")
        self.client.login(username="trener", password="testpass123")
        self.session = TrainingSession.objects.create(
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0), end_time=time(11, 0), capacity=1,
        )
        self.owner = Owner.objects.create(first_name="Ola", last_name="Test", phone="600111222")
        self.dog = Dog.objects.create(name="Pixel", owner=self.owner)

    def test_anonymous_redirected_to_login(self):
        self.client.logout()
        response = self.client.get("/scheduling/")
        self.assertEqual(response.status_code, 302)

    def test_booking_existing_dog_success(self):
        response = self.client.post(
            f"/scheduling/sessions/{self.session.pk}/bookings/add-existing/",
            {"dog": self.dog.pk, "linked_plan": "", "notes": ""}
        )
        self.assertEqual(response.status_code, 302)
        booking = Booking.objects.get(session=self.session, dog=self.dog)
        self.assertEqual(booking.status, Booking.STATUS_CONFIRMED)

    def test_booking_duplicate_dog_blocked_by_validation(self):
        Booking.objects.create(session=self.session, dog=self.dog, status=Booking.STATUS_CONFIRMED)
        response = self.client.post(
            f"/scheduling/sessions/{self.session.pk}/bookings/add-existing/",
            {"dog": self.dog.pk, "linked_plan": "", "notes": ""}
        )
        self.assertEqual(response.status_code, 200)  # formularz z bledem, nie redirect
        self.assertEqual(Booking.objects.filter(session=self.session, dog=self.dog).count(), 1)

    def test_booking_full_session_goes_to_waiting_list(self):
        dog2 = Dog.objects.create(name="Reksio", owner=self.owner)
        Booking.objects.create(session=self.session, dog=self.dog, status=Booking.STATUS_CONFIRMED)
        response = self.client.post(
            f"/scheduling/sessions/{self.session.pk}/bookings/add-existing/",
            {"dog": dog2.pk, "linked_plan": "", "notes": ""}
        )
        self.assertEqual(response.status_code, 302)
        booking = Booking.objects.get(session=self.session, dog=dog2)
        self.assertEqual(booking.status, Booking.STATUS_WAITING_LIST)

    def test_new_client_booking_creates_owner_and_dog(self):
        response = self.client.post(
            f"/scheduling/sessions/{self.session.pk}/bookings/add-new/",
            {"first_name": "Nowy", "last_name": "Klient", "phone": "600999888", "dog_name": "Burek", "notes": ""}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Owner.objects.filter(phone="600999888").exists())
        self.assertTrue(Dog.objects.filter(name="Burek").exists())

    def test_new_client_booking_deduplicates_by_phone(self):
        """KRYTYCZNY test: ten sam numer telefonu dwa razy -> NIE tworzy
        duplikatu Owner, drugi pies podlinkowany do istniejacego klienta."""
        session2 = TrainingSession.objects.create(
            date=date.today() + timedelta(days=2),
            start_time=time(14, 0), end_time=time(15, 0), capacity=5,
        )
        self.client.post(
            f"/scheduling/sessions/{self.session.pk}/bookings/add-new/",
            {"first_name": "Anna", "last_name": "Nowak", "phone": "600777888", "dog_name": "Azor", "notes": ""}
        )
        self.client.post(
            f"/scheduling/sessions/{session2.pk}/bookings/add-new/",
            {"first_name": "Anna", "last_name": "Nowak", "phone": "600777888", "dog_name": "Luna", "notes": ""}
        )
        self.assertEqual(Owner.objects.filter(phone="600777888").count(), 1)
        owner = Owner.objects.get(phone="600777888")
        self.assertEqual(owner.dogs.count(), 2)

    def test_session_cancel_cascades_bookings(self):
        Booking.objects.create(session=self.session, dog=self.dog, status=Booking.STATUS_CONFIRMED)
        response = self.client.post(f"/scheduling/sessions/{self.session.pk}/delete/")
        self.assertEqual(response.status_code, 302)
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, TrainingSession.STATUS_CANCELLED)
        booking = Booking.objects.get(session=self.session, dog=self.dog)
        self.assertEqual(booking.status, Booking.STATUS_CANCELLED)

    def test_session_duplicate_view(self):
        response = self.client.post(f"/scheduling/sessions/{self.session.pk}/duplicate/")
        self.assertEqual(response.status_code, 302)
        new_session = TrainingSession.objects.filter(date=self.session.date + timedelta(days=7))
        self.assertEqual(new_session.count(), 1)

    def test_booking_status_cancel_promotes_waiting_list(self):
        dog2 = Dog.objects.create(name="Reksio", owner=self.owner)
        confirmed = Booking.objects.create(session=self.session, dog=self.dog, status=Booking.STATUS_CONFIRMED)
        waiting = Booking.objects.create(session=self.session, dog=dog2, status=Booking.STATUS_WAITING_LIST)

        response = self.client.post(f"/scheduling/bookings/{confirmed.pk}/status/cancelled/")
        self.assertEqual(response.status_code, 302)

        waiting.refresh_from_db()
        self.assertEqual(waiting.status, Booking.STATUS_CONFIRMED)

    def test_calendar_feed_returns_json(self):
        response = self.client.get("/scheduling/calendar/feed/?start=2020-01-01&end=2030-01-01")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")


class PendingBookingRequestModelTest(TestCase):
    """Testy modelu kwarantanny dla gosci (Etap 4 - przyszlosciowy, ale
    model juz istnieje). Weryfikuje ze wniosek NIE tworzy automatycznie
    zadnego Owner/Dog/Booking - to tylko dane do recznej weryfikacji."""

    def setUp(self):
        self.session = TrainingSession.objects.create(
            date=date.today() + timedelta(days=1),
            start_time=time(10, 0), end_time=time(11, 0), capacity=5, is_public=True,
        )

    def test_pending_request_creation_does_not_create_owner_or_dog(self):
        initial_owner_count = Owner.objects.count()
        initial_dog_count = Dog.objects.count()

        PendingBookingRequest.objects.create(
            session=self.session, submitted_name="Jan Testowy", submitted_phone="600111222",
            dog_name="Reksio", message="Chcialbym zapisac psa",
        )

        self.assertEqual(Owner.objects.count(), initial_owner_count)
        self.assertEqual(Dog.objects.count(), initial_dog_count)
        self.assertEqual(Booking.objects.count(), 0)

    def test_pending_request_default_status_is_pending(self):
        req = PendingBookingRequest.objects.create(
            session=self.session, submitted_name="Jan Testowy", submitted_phone="600111222",
            dog_name="Reksio",
        )
        self.assertEqual(req.status, PendingBookingRequest.STATUS_PENDING)



# ============================================================
# ETAP 4: Publiczne zapisy + moderacja wnioskow
# ============================================================

from django.utils import timezone
from .models import PendingBookingRequest


class PublicSessionListViewTest(TestCase):
    """Testy publicznej listy terminow - bez logowania."""

    def setUp(self):
        self.session_public = TrainingSession.objects.create(
            title="Publiczny", date=date.today() + timedelta(days=3),
            start_time=time(10, 0), end_time=time(11, 0), capacity=2, is_public=True,
        )
        self.session_private = TrainingSession.objects.create(
            title="Prywatny", date=date.today() + timedelta(days=3),
            start_time=time(12, 0), end_time=time(13, 0), capacity=2, is_public=False,
        )
        self.session_past = TrainingSession.objects.create(
            title="Z przeszlosci", date=date.today() - timedelta(days=1),
            start_time=time(10, 0), end_time=time(11, 0), capacity=2, is_public=True,
        )

    def test_accessible_without_login(self):
        response = self.client.get("/scheduling/public/")
        self.assertEqual(response.status_code, 200)

    def test_shows_only_public_sessions(self):
        response = self.client.get("/scheduling/public/")
        content = response.content.decode()
        self.assertIn("Publiczny", content)
        self.assertNotIn("Prywatny", content)

    def test_hides_past_sessions(self):
        response = self.client.get("/scheduling/public/")
        content = response.content.decode()
        self.assertNotIn("Z przeszlosci", content)

    def test_range_filter_7_days(self):
        far_session = TrainingSession.objects.create(
            title="Daleki termin", date=date.today() + timedelta(days=20),
            start_time=time(10, 0), end_time=time(11, 0), capacity=2, is_public=True,
        )
        response = self.client.get("/scheduling/public/?range=7")
        content = response.content.decode()
        self.assertIn("Publiczny", content)
        self.assertNotIn("Daleki termin", content)


class TrainingSessionPubliclyBookableTest(TestCase):
    def test_is_publicly_bookable_true_for_valid_session(self):
        session = TrainingSession.objects.create(
            date=date.today() + timedelta(days=1), start_time=time(10, 0),
            end_time=time(11, 0), capacity=1, is_public=True,
        )
        self.assertTrue(session.is_publicly_bookable())

    def test_is_publicly_bookable_false_when_not_public(self):
        session = TrainingSession.objects.create(
            date=date.today() + timedelta(days=1), start_time=time(10, 0),
            end_time=time(11, 0), capacity=1, is_public=False,
        )
        self.assertFalse(session.is_publicly_bookable())

    def test_is_publicly_bookable_false_when_cancelled(self):
        session = TrainingSession.objects.create(
            date=date.today() + timedelta(days=1), start_time=time(10, 0),
            end_time=time(11, 0), capacity=1, is_public=True,
            status=TrainingSession.STATUS_CANCELLED,
        )
        self.assertFalse(session.is_publicly_bookable())

    def test_is_publicly_bookable_false_when_past(self):
        session = TrainingSession.objects.create(
            date=date.today() - timedelta(days=1), start_time=time(10, 0),
            end_time=time(11, 0), capacity=1, is_public=True,
        )
        self.assertFalse(session.is_publicly_bookable())


class PublicBookingRequestViewTest(TestCase):
    """Testy formularza publicznego zgloszenia (bez logowania)."""

    def setUp(self):
        self.session = TrainingSession.objects.create(
            date=date.today() + timedelta(days=3), start_time=time(10, 0),
            end_time=time(11, 0), capacity=1, is_public=True,
        )
        self.valid_data = {
            "submitted_name": "Jan Nowak", "submitted_phone": "600777888",
            "submitted_email": "", "dog_name": "Burek", "message": "",
            "rodo_consent": "on", "website": "",
        }

    def test_get_form_on_non_public_session_404(self):
        private_session = TrainingSession.objects.create(
            date=date.today() + timedelta(days=3), start_time=time(12, 0),
            end_time=time(13, 0), capacity=1, is_public=False,
        )
        response = self.client.get(f"/scheduling/public/{private_session.pk}/zapisz/")
        self.assertEqual(response.status_code, 404)

    def test_valid_submission_creates_pending_request_not_owner_or_dog(self):
        from clients.models import Owner, Dog
        owner_count_before = Owner.objects.count()
        dog_count_before = Dog.objects.count()

        response = self.client.post(f"/scheduling/public/{self.session.pk}/zapisz/", self.valid_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Owner.objects.count(), owner_count_before)
        self.assertEqual(Dog.objects.count(), dog_count_before)

        req = PendingBookingRequest.objects.get(submitted_phone="600777888")
        self.assertEqual(req.status, PendingBookingRequest.STATUS_PENDING)
        self.assertTrue(req.rodo_consent)

    def test_honeypot_filled_does_not_create_request(self):
        data = dict(self.valid_data)
        data["website"] = "http://spam.example.com"
        count_before = PendingBookingRequest.objects.count()

        response = self.client.post(f"/scheduling/public/{self.session.pk}/zapisz/", data)
        self.assertEqual(response.status_code, 302)  # wciaz "sukces" dla bota
        self.assertEqual(PendingBookingRequest.objects.count(), count_before)

    def test_missing_rodo_consent_rejected(self):
        data = dict(self.valid_data)
        data["rodo_consent"] = ""
        response = self.client.post(f"/scheduling/public/{self.session.pk}/zapisz/", data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(PendingBookingRequest.objects.filter(submitted_phone="600777888").exists())

    def test_duplicate_phone_same_session_blocked(self):
        self.client.post(f"/scheduling/public/{self.session.pk}/zapisz/", self.valid_data)
        response = self.client.post(f"/scheduling/public/{self.session.pk}/zapisz/", self.valid_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Juz wyslano zgloszenie", response.content.decode())
        self.assertEqual(
            PendingBookingRequest.objects.filter(submitted_phone="600777888").count(), 1
        )

    def test_rate_limit_blocks_after_threshold(self):
        for i in range(3):
            data = dict(self.valid_data)
            data["submitted_phone"] = f"60000000{i}"
            self.client.post(f"/scheduling/public/{self.session.pk}/zapisz/", data)

        data = dict(self.valid_data)
        data["submitted_phone"] = "600000099"
        response = self.client.post(f"/scheduling/public/{self.session.pk}/zapisz/", data)
        self.assertIn("Zbyt wiele zgloszen", response.content.decode())


class PendingBookingRequestApproveRejectTest(TestCase):
    """Testy metod approve()/reject() modelu + widokow moderacji."""

    def setUp(self):
        self.user = User.objects.create_user(username="trener", password="testpass123")
        self.client.login(username="trener", password="testpass123")
        self.session = TrainingSession.objects.create(
            date=date.today() + timedelta(days=3), start_time=time(10, 0),
            end_time=time(11, 0), capacity=1,
        )
        self.owner = Owner.objects.create(first_name="Ola", last_name="Test", phone="600111222")

    def test_approve_creates_owner_dog_booking(self):
        from clients.models import Owner, Dog
        req = PendingBookingRequest.objects.create(
            session=self.session, submitted_name="Jan Nowak", submitted_phone="600999888",
            dog_name="Burek", rodo_consent=True,
        )
        result = req.approve(user=self.user)

        self.assertTrue(Owner.objects.filter(phone="600999888").exists())
        self.assertTrue(Dog.objects.filter(name="Burek").exists())
        self.assertEqual(result["booking"].status, Booking.STATUS_CONFIRMED)
        req.refresh_from_db()
        self.assertEqual(req.status, PendingBookingRequest.STATUS_APPROVED)
        self.assertEqual(req.decided_by, self.user)

    def test_approve_deduplicates_by_phone(self):
        req = PendingBookingRequest.objects.create(
            session=self.session, submitted_name="Ola Inna Pisownia", submitted_phone="600111222",
            dog_name="NowyPies", rodo_consent=True,
        )
        owner_count_before = Owner.objects.count()
        result = req.approve(user=self.user)

        self.assertEqual(Owner.objects.count(), owner_count_before)
        self.assertTrue(result["matched_existing_owner"])
        self.assertEqual(result["owner"], self.owner)

    def test_approve_goes_to_waiting_list_when_full(self):
        dog_existing = Dog.objects.create(name="Pixel", owner=self.owner)
        Booking.objects.create(session=self.session, dog=dog_existing, status=Booking.STATUS_CONFIRMED)

        req = PendingBookingRequest.objects.create(
            session=self.session, submitted_name="Jan Nowak", submitted_phone="600999888",
            dog_name="Burek", rodo_consent=True,
        )
        result = req.approve(user=self.user)
        self.assertTrue(result["went_to_waiting_list"])
        self.assertEqual(result["booking"].status, Booking.STATUS_WAITING_LIST)

    def test_approve_raises_if_already_decided(self):
        req = PendingBookingRequest.objects.create(
            session=self.session, submitted_name="Jan Nowak", submitted_phone="600999888",
            dog_name="Burek", rodo_consent=True, status=PendingBookingRequest.STATUS_APPROVED,
        )
        with self.assertRaises(ValueError):
            req.approve(user=self.user)

    def test_reject_creates_no_owner_or_dog(self):
        from clients.models import Owner, Dog
        owner_count_before = Owner.objects.count()
        dog_count_before = Dog.objects.count()

        req = PendingBookingRequest.objects.create(
            session=self.session, submitted_name="Spam", submitted_phone="000000000",
            dog_name="FalszywyPies", rodo_consent=True,
        )
        req.reject(user=self.user, note="spam")

        self.assertEqual(Owner.objects.count(), owner_count_before)
        self.assertEqual(Dog.objects.count(), dog_count_before)
        req.refresh_from_db()
        self.assertEqual(req.status, PendingBookingRequest.STATUS_REJECTED)
        self.assertEqual(req.rejection_note, "spam")

    def test_reject_raises_if_already_decided(self):
        req = PendingBookingRequest.objects.create(
            session=self.session, submitted_name="Jan", submitted_phone="600999888",
            dog_name="Burek", rodo_consent=True, status=PendingBookingRequest.STATUS_REJECTED,
        )
        with self.assertRaises(ValueError):
            req.reject(user=self.user)

    def test_pending_request_list_requires_login(self):
        self.client.logout()
        response = self.client.get("/scheduling/pending-requests/")
        self.assertEqual(response.status_code, 302)

    def test_approve_view_integration(self):
        req = PendingBookingRequest.objects.create(
            session=self.session, submitted_name="Jan Nowak", submitted_phone="600999888",
            dog_name="Burek", rodo_consent=True,
        )
        response = self.client.post(f"/scheduling/pending-requests/{req.pk}/approve/")
        self.assertEqual(response.status_code, 302)
        req.refresh_from_db()
        self.assertEqual(req.status, PendingBookingRequest.STATUS_APPROVED)

    def test_reject_view_integration(self):
        req = PendingBookingRequest.objects.create(
            session=self.session, submitted_name="Jan Nowak", submitted_phone="600999888",
            dog_name="Burek", rodo_consent=True,
        )
        response = self.client.post(f"/scheduling/pending-requests/{req.pk}/reject/", {"rejection_note": "test"})
        self.assertEqual(response.status_code, 302)
        req.refresh_from_db()
        self.assertEqual(req.status, PendingBookingRequest.STATUS_REJECTED)


class SplitFullNameTest(TestCase):
    def test_two_words(self):
        from .models import split_full_name
        self.assertEqual(split_full_name("Jan Nowak"), ("Jan", "Nowak"))

    def test_single_word(self):
        from .models import split_full_name
        self.assertEqual(split_full_name("Jan"), ("Jan", ""))

    def test_three_words(self):
        from .models import split_full_name
        self.assertEqual(split_full_name("Jan Maria Nowak"), ("Jan", "Maria Nowak"))

    def test_empty_string(self):
        from .models import split_full_name
        self.assertEqual(split_full_name(""), ("", ""))



# ============ DZIENNIK TRENINGOWY (notatka przy Booking) ============

class BookingJournalTest(TestCase):
    """Testy dziennika treningowego - notatka z treningu przy rezerwacji,
    opcjonalna, mozliwa do uzupelnienia w kazdym momencie."""

    def setUp(self):
        self.user = User.objects.create_user(username="trener2", password="testpass123")
        self.client.login(username="trener2", password="testpass123")
        self.session = TrainingSession.objects.create(
            date=date.today(), start_time=time(10, 0), end_time=time(11, 0), capacity=1,
        )
        self.owner = Owner.objects.create(first_name="Ola", last_name="Test", phone="600111222")
        self.dog = Dog.objects.create(name="Pixel", owner=self.owner)
        self.booking = Booking.objects.create(session=self.session, dog=self.dog, status=Booking.STATUS_CONFIRMED)

    def test_has_journal_entry_false_by_default(self):
        self.assertFalse(self.booking.has_journal_entry())

    def test_has_journal_entry_true_after_save(self):
        self.booking.journal_entry = "Dobry trening."
        self.booking.save()
        self.assertTrue(self.booking.has_journal_entry())

    def test_attended_status_redirects_to_journal_form(self):
        response = self.client.post(f"/scheduling/bookings/{self.booking.pk}/status/attended/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"/scheduling/bookings/{self.booking.pk}/journal/")

    def test_no_show_status_does_not_redirect_to_journal(self):
        response = self.client.post(f"/scheduling/bookings/{self.booking.pk}/status/no_show/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"/scheduling/sessions/{self.session.pk}/")

    def test_journal_form_get_shows_dog_name(self):
        response = self.client.get(f"/scheduling/bookings/{self.booking.pk}/journal/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pixel")

    def test_journal_form_post_saves_entry(self):
        response = self.client.post(f"/scheduling/bookings/{self.booking.pk}/journal/", {
            "journal_entry": "Pracowalismy na rownowadze, pies spiety w tylnych lapach.",
        })
        self.assertEqual(response.status_code, 302)
        self.booking.refresh_from_db()
        self.assertIn("rownowadze", self.booking.journal_entry)

    def test_journal_form_allows_empty_entry(self):
        response = self.client.post(f"/scheduling/bookings/{self.booking.pk}/journal/", {
            "journal_entry": "",
        })
        self.assertEqual(response.status_code, 302)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.journal_entry, "")

    def test_anonymous_cannot_access_journal_form(self):
        self.client.logout()
        response = self.client.get(f"/scheduling/bookings/{self.booking.pk}/journal/")
        self.assertEqual(response.status_code, 302)

    def test_session_detail_shows_completed_bookings_section(self):
        self.booking.status = Booking.STATUS_ATTENDED
        self.booking.save()
        response = self.client.get(f"/scheduling/sessions/{self.session.pk}/")
        self.assertContains(response, "Obecni / Nieobecni")
        self.assertContains(response, "Pixel")


class DogDetailTrainingHistoryTest(TestCase):
    """Testy historii treningow (odnosnik z karty psa)."""

    def setUp(self):
        self.user = User.objects.create_user(username="trener3", password="testpass123")
        self.client.login(username="trener3", password="testpass123")
        self.owner = Owner.objects.create(first_name="Ola", last_name="Test", phone="600111222")
        self.dog = Dog.objects.create(name="Pixel", owner=self.owner)
        self.session = TrainingSession.objects.create(
            date=date.today(), start_time=time(10, 0), end_time=time(11, 0), capacity=1,
        )
        self.booking = Booking.objects.create(
            session=self.session, dog=self.dog, status=Booking.STATUS_ATTENDED,
            journal_entry="Swietny trening, duzy postep.",
        )

    def test_dog_detail_shows_training_history_section(self):
        response = self.client.get(f"/dogs/{self.dog.pk}/")
        self.assertContains(response, "Historia treningow")
        self.assertContains(response, "Swietny trening")

    def test_dog_detail_links_to_session_and_journal_edit(self):
        response = self.client.get(f"/dogs/{self.dog.pk}/")
        self.assertContains(response, f"/scheduling/sessions/{self.session.pk}/")
        self.assertContains(response, f"/scheduling/bookings/{self.booking.pk}/journal/")

    def test_dog_without_history_shows_empty_state(self):
        empty_dog = Dog.objects.create(name="BezHistorii", owner=self.owner)
        response = self.client.get(f"/dogs/{empty_dog.pk}/")
        self.assertContains(response, "Brak historii treningow")
