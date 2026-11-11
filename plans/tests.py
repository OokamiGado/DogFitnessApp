from django.test import TestCase
from django.contrib.auth.models import User
from clients.models import Owner, Dog
from exercises.models import Exercise, MuscleGroup
from .models import (
    TrainingPlan, ExerciseSet, PlanExercise, BrandingProfile,
    format_frequency,
)


class FormatFrequencyTest(TestCase):
    def test_single_value(self):
        self.assertEqual(format_frequency(3, 3, 'week'), "3x w tygodniu")

    def test_single_value_only_min(self):
        self.assertEqual(format_frequency(3, None, 'week'), "3x w tygodniu")

    def test_range(self):
        self.assertEqual(format_frequency(0, 1, 'week'), "0-1x w tygodniu")

    def test_no_data_returns_empty(self):
        self.assertEqual(format_frequency(None, None, 'week'), "")

    def test_day_period(self):
        self.assertEqual(format_frequency(2, 2, 'day'), "2x dziennie")


class BrandingProfileModelTest(TestCase):
    def test_only_one_default_allowed(self):
        bp1 = BrandingProfile.objects.create(name="Profil 1", is_default=True)
        bp2 = BrandingProfile.objects.create(name="Profil 2", is_default=True)
        bp1.refresh_from_db()
        self.assertFalse(bp1.is_default)
        self.assertTrue(bp2.is_default)

    def test_get_default_returns_default_profile(self):
        BrandingProfile.objects.create(name="Nie domyslny", is_default=False)
        default_profile = BrandingProfile.objects.create(name="Domyslny", is_default=True)
        self.assertEqual(BrandingProfile.get_default(), default_profile)

    def test_get_default_returns_first_if_none_marked(self):
        bp = BrandingProfile.objects.create(name="Jedyny", is_default=False)
        self.assertEqual(BrandingProfile.get_default(), bp)

    def test_get_default_returns_none_if_empty(self):
        self.assertIsNone(BrandingProfile.get_default())


class TrainingPlanModelTest(TestCase):
    def setUp(self):
        self.owner = Owner.objects.create(first_name="Ola", last_name="Test", phone="600111222")
        self.dog = Dog.objects.create(name="Pixel", owner=self.owner)
        self.mg = MuscleGroup.objects.create(name="Core")
        self.ex = Exercise.objects.create(name="Test cwiczenie", description="x", difficulty="easy")

    def test_str_includes_dog_name(self):
        plan = TrainingPlan.objects.create(dog=self.dog, name="Plan testowy")
        self.assertIn("Pixel", str(plan))

    def test_get_conflicts_empty_when_no_shared_tags(self):
        plan = TrainingPlan.objects.create(dog=self.dog, name="Plan testowy")
        es = ExerciseSet.objects.create(plan=plan, order=0)
        PlanExercise.objects.create(exercise_set=es, exercise=self.ex, order=0)
        self.assertEqual(plan.get_conflicts(), [])

    def test_get_conflicts_detects_shared_tag(self):
        from exercises.models import ContraindicationTag
        tag = ContraindicationTag.objects.create(name="Dysplazja")
        self.dog.health_tags.add(tag)
        self.ex.contraindication_tags.add(tag)

        plan = TrainingPlan.objects.create(dog=self.dog, name="Plan testowy")
        es = ExerciseSet.objects.create(plan=plan, order=0)
        PlanExercise.objects.create(exercise_set=es, exercise=self.ex, order=0)

        conflicts = plan.get_conflicts()
        self.assertEqual(len(conflicts), 1)


class PlanDocumentGenerationTest(TestCase):
    """Testy generowania PDF/DOCX - weryfikuja ze funkcje nie wywalaja
    wyjatkow i produkuja niepusta zawartosc (nie testujemy dokladnej
    tresci wizualnej, tylko ze mechanizm dziala)."""

    def setUp(self):
        self.owner = Owner.objects.create(first_name="Ola", last_name="Test", phone="600111222")
        self.dog = Dog.objects.create(name="Pixel", owner=self.owner, breed="Border Collie")
        self.ex = Exercise.objects.create(name="Test cwiczenie", description="x", difficulty="easy")
        self.plan = TrainingPlan.objects.create(
            dog=self.dog, name="Plan testowy", training_goal="Cel testowy"
        )
        es = ExerciseSet.objects.create(plan=self.plan, name="Zestaw 1", order=0)
        PlanExercise.objects.create(
            exercise_set=es, exercise=self.ex, order=0,
            goal_text="Cel", execution_text="Wykonanie z polskimi znakami: łąka żółw",
            reps_text="5x",
        )
        self.branding = BrandingProfile.objects.create(name="Test", is_default=True)

    def test_generate_detailed_pdf_produces_valid_pdf(self):
        from .document_generation import generate_detailed_pdf
        buf = generate_detailed_pdf(self.plan, self.branding)
        content = buf.getvalue()
        self.assertTrue(content.startswith(b"%PDF"))
        self.assertGreater(len(content), 100)

    def test_generate_fiszka_pdf_produces_valid_pdf(self):
        from .document_generation import generate_fiszka_pdf
        buf = generate_fiszka_pdf(self.plan, self.branding)
        content = buf.getvalue()
        self.assertTrue(content.startswith(b"%PDF"))

    def test_generate_detailed_docx_produces_valid_docx(self):
        from .document_generation import generate_detailed_docx
        buf = generate_detailed_docx(self.plan, self.branding)
        content = buf.getvalue()
        # DOCX = zip file, zaczyna sie od magic bytes PK
        self.assertTrue(content.startswith(b"PK"))

    def test_generate_fiszka_docx_produces_valid_docx(self):
        from .document_generation import generate_fiszka_docx
        buf = generate_fiszka_docx(self.plan, self.branding)
        content = buf.getvalue()
        self.assertTrue(content.startswith(b"PK"))

    def test_generate_pdf_works_without_branding(self):
        """Krytyczny test: generowanie PDF NIE MOZE sie wywalic, jesli
        w bazie nie ma zadnego BrandingProfile (branding=None)."""
        from .document_generation import generate_detailed_pdf
        buf = generate_detailed_pdf(self.plan, None)
        self.assertTrue(buf.getvalue().startswith(b"%PDF"))


class PlanDownloadViewsTest(TestCase):
    """Testy integracyjne widokow download - weryfikuja poprawny
    Content-Disposition z polskimi znakami w nazwie planu (RFC 6266)."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.login(username="testuser", password="testpass123")
        self.owner = Owner.objects.create(first_name="Ola", last_name="Test", phone="600111222")
        self.dog = Dog.objects.create(name="Żaba", owner=self.owner)
        self.plan = TrainingPlan.objects.create(dog=self.dog, name="Plan Żółwia Łąka")
        BrandingProfile.objects.create(name="Domyslny", is_default=True)

    def test_detailed_pdf_download_returns_200(self):
        response = self.client.get(f"/plans/{self.plan.pk}/download/detailed-pdf/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_content_disposition_has_ascii_fallback_and_utf8_variant(self):
        """Weryfikuje ze naglowek Content-Disposition zawiera OBA warianty
        (ASCII fallback + filename* UTF-8) - RFC 6266 - dla polskich znakow
        w nazwie planu, ktore wczesniej powodowaly nieprawidlowe kodowanie
        MIME encoded-word (RFC 2047) nieczytelne dla wielu przegladarek."""
        response = self.client.get(f"/plans/{self.plan.pk}/download/detailed-pdf/")
        disposition = response["Content-Disposition"]
        self.assertIn("filename=", disposition)
        self.assertIn("filename*=UTF-8''", disposition)
        # NIE powinno zawierac MIME encoded-word (ktory byl bugiem wczesniej)
        self.assertNotIn("=?utf-8?", disposition)

    def test_anonymous_cannot_download(self):
        self.client.logout()
        response = self.client.get(f"/plans/{self.plan.pk}/download/detailed-pdf/")
        self.assertEqual(response.status_code, 302)
