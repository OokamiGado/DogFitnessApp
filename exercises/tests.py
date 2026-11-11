from django.test import TestCase
from .models import MuscleGroup, Equipment, Exercise, ContraindicationTag


class MuscleGroupModelTest(TestCase):
    def test_str_returns_name(self):
        mg = MuscleGroup.objects.create(name="Core")
        self.assertEqual(str(mg), "Core")


class ExerciseModelTest(TestCase):
    def setUp(self):
        self.mg = MuscleGroup.objects.create(name="Core")

    def test_str_returns_name(self):
        ex = Exercise.objects.create(name="Test cwiczenie", description="opis", difficulty="easy")
        self.assertEqual(str(ex), "Test cwiczenie")

    def test_get_root_returns_self_when_no_parent(self):
        ex = Exercise.objects.create(name="Glowne", description="x", difficulty="easy")
        self.assertEqual(ex.get_root(), ex)

    def test_get_root_returns_parent_for_variant(self):
        parent = Exercise.objects.create(name="Glowne", description="x", difficulty="easy")
        variant = Exercise.objects.create(
            name="Wariant", description="x", difficulty="hard",
            parent_exercise=parent, variant_name="Zaawansowany"
        )
        self.assertEqual(variant.get_root(), parent)

    def test_get_youtube_embed_url_valid_link(self):
        ex = Exercise.objects.create(
            name="Test", description="x", difficulty="easy",
            video_url="https://www.youtube.com/watch?v=abc123"
        )
        self.assertEqual(ex.get_youtube_embed_url(), "https://www.youtube.com/embed/abc123")

    def test_get_youtube_embed_url_invalid_link_returns_none(self):
        ex = Exercise.objects.create(
            name="Test", description="x", difficulty="easy",
            video_url="https://example.com/not-youtube"
        )
        self.assertIsNone(ex.get_youtube_embed_url())

    def test_get_youtube_embed_url_no_link_returns_none(self):
        ex = Exercise.objects.create(name="Test", description="x", difficulty="easy")
        self.assertIsNone(ex.get_youtube_embed_url())

    def test_is_active_default_true(self):
        ex = Exercise.objects.create(name="Test", description="x", difficulty="easy")
        self.assertTrue(ex.is_active)


class ExerciseListViewTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.client.login(username="testuser", password="testpass123")

    def test_anonymous_redirected_to_login(self):
        self.client.logout()
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_logged_in_user_sees_exercise_list(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
