from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth.models import User
from .models import Owner, Dog, AuditLog


class OwnerModelTest(TestCase):
    def test_full_name_property(self):
        owner = Owner.objects.create(first_name="Anna", last_name="Nowak", phone="600111222")
        self.assertEqual(owner.full_name, "Anna Nowak")

    def test_str_returns_full_name(self):
        owner = Owner.objects.create(first_name="Anna", last_name="Nowak", phone="600111222")
        self.assertEqual(str(owner), "Anna Nowak")

    def test_rodo_consent_date_set_automatically(self):
        owner = Owner.objects.create(
            first_name="Anna", last_name="Nowak", phone="600111222", rodo_consent=True
        )
        self.assertIsNotNone(owner.rodo_consent_date)
        self.assertEqual(owner.rodo_consent_date, date.today())

    def test_rodo_consent_date_cleared_when_consent_false(self):
        owner = Owner.objects.create(
            first_name="Anna", last_name="Nowak", phone="600111222", rodo_consent=True
        )
        owner.rodo_consent = False
        owner.save()
        self.assertIsNone(owner.rodo_consent_date)

    def test_active_dogs_excludes_archived(self):
        owner = Owner.objects.create(first_name="Anna", last_name="Nowak", phone="600111222")
        Dog.objects.create(name="Aktywny", owner=owner, is_active=True)
        Dog.objects.create(name="Zarchiwizowany", owner=owner, is_active=False)
        self.assertEqual(owner.active_dogs().count(), 1)


class DogModelTest(TestCase):
    def setUp(self):
        self.owner = Owner.objects.create(first_name="Anna", last_name="Nowak", phone="600111222")

    def test_str_returns_name(self):
        dog = Dog.objects.create(name="Pixel", owner=self.owner)
        self.assertEqual(str(dog), "Pixel")

    def test_get_age_display_no_birth_date_returns_none(self):
        dog = Dog.objects.create(name="Pixel", owner=self.owner)
        self.assertIsNone(dog.get_age_display())

    def test_get_age_display_future_date_returns_none(self):
        dog = Dog.objects.create(
            name="Pixel", owner=self.owner, birth_date=date.today() + timedelta(days=10)
        )
        self.assertIsNone(dog.get_age_display())

    def test_get_age_display_adult_dog(self):
        birth = date.today().replace(year=date.today().year - 5)
        dog = Dog.objects.create(name="Pixel", owner=self.owner, birth_date=birth)
        age_text = dog.get_age_display()
        self.assertIn("5", age_text)

    def test_get_age_display_puppy_under_one_month(self):
        birth = date.today() - timedelta(days=5)
        dog = Dog.objects.create(name="Szczeniak", owner=self.owner, birth_date=birth)
        self.assertEqual(dog.get_age_display(), "poniżej miesiąca")

    def test_get_shared_tags_no_health_tags_returns_empty(self):
        from exercises.models import Exercise
        dog = Dog.objects.create(name="Pixel", owner=self.owner)
        ex = Exercise.objects.create(name="Test", description="x", difficulty="easy")
        self.assertEqual(dog.get_shared_tags(ex), [])

    def test_get_shared_tags_returns_common_tags(self):
        from exercises.models import Exercise, ContraindicationTag
        tag = ContraindicationTag.objects.create(name="Dysplazja")
        dog = Dog.objects.create(name="Pixel", owner=self.owner)
        dog.health_tags.add(tag)
        ex = Exercise.objects.create(name="Test", description="x", difficulty="easy")
        ex.contraindication_tags.add(tag)
        shared = dog.get_shared_tags(ex)
        self.assertEqual(len(shared), 1)
        self.assertEqual(shared[0], tag)


class OwnerViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.login(username="testuser", password="testpass123")

    def test_anonymous_redirected_to_login(self):
        self.client.logout()
        response = self.client.get("/clients/")
        self.assertEqual(response.status_code, 302)

    def test_owner_list_accessible_when_logged_in(self):
        response = self.client.get("/clients/")
        self.assertEqual(response.status_code, 200)

    def test_owner_create_valid_data_redirects(self):
        response = self.client.post("/clients/add/", {
            "first_name": "Jan", "last_name": "Testowy", "phone": "600111222",
            "email": "", "address": "", "notes": "",
            "secondary_contact_name": "", "secondary_contact_phone": "",
            "rodo_consent": "on", "photo_consent": "",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Owner.objects.filter(first_name="Jan", last_name="Testowy").exists())


class AuditLogTest(TestCase):
    def test_log_entry_created_on_owner_create(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.login(username="testuser", password="testpass123")
        self.client.post("/clients/add/", {
            "first_name": "Jan", "last_name": "Testowy", "phone": "600111222",
            "email": "", "address": "", "notes": "",
            "secondary_contact_name": "", "secondary_contact_phone": "",
            "rodo_consent": "", "photo_consent": "",
        })
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.ACTION_CREATED).exists())


class DogPdfViewTest(TestCase):
    """Testy generowania karty psa PDF - weryfikuja poprawna obsluge
    polskich znakow (fonty TTF DejaVu) oraz Content-Disposition (RFC 6266)."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.login(username="testuser", password="testpass123")
        self.owner = Owner.objects.create(first_name="Ola", last_name="Test", phone="600111222")
        self.dog = Dog.objects.create(
            name="Żaba", owner=self.owner, breed="Owczarek",
            health_notes="Uwaga na łapy i dysplazję"
        )

    def test_dog_pdf_returns_valid_pdf(self):
        response = self.client.get(f"/dogs/{self.dog.pk}/pdf/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_dog_pdf_content_disposition_rfc6266(self):
        """Nazwa psa z polskimi znakami (Żaba) musi dac poprawny naglowek
        Content-Disposition z ASCII fallback + filename* UTF-8."""
        response = self.client.get(f"/dogs/{self.dog.pk}/pdf/")
        disposition = response["Content-Disposition"]
        self.assertIn("filename*=UTF-8''", disposition)
