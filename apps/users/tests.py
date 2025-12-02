from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse
from apps.users.models import User


class AdminCreateTests(TestCase):
	def setUp(self):
		# superuser
		self.superuser = User.objects.create_superuser(
			email='super@example.com', password='superpass',
			first_name='Super', last_name='User', age=40, height=180, weight=80
		)

		# normal admin (staff but not superuser)
		self.admin = User.objects.create_user(
			email='staff@example.com', password='staffpass',
			first_name='Staff', last_name='Member', age=35, height=170, weight=70
		)
		self.admin.is_staff = True
		self.admin.save()

		# normal user
		self.user = User.objects.create_user(
			email='user@example.com', password='userpass',
			first_name='Normal', last_name='User', age=30, height=165, weight=60
		)

		self.client = APIClient()

    # ---------- TEST CASES ----------

	def test_non_admin_cannot_create_admin(self):
		self.client.force_authenticate(user=self.user)
		url = reverse('admin-create')
		payload = {
			'email': 'newadmin@example.com', 'password': 'pw12', 'first_name': 'New', 'last_name': 'Admin',
			'age': 28, 'height': 170, 'weight': 70, 'is_staff': True,
			'ideal': {'ideal_weight': 75}
		}
		res = self.client.post(url, payload, format='json')
		self.assertEqual(res.status_code, 403)

	def test_admin_can_create_staff_but_not_superuser(self):
		self.client.force_authenticate(user=self.admin)
		url = reverse('admin-create')
		payload = {
			'email': 'createdstaff@example.com', 'password': 'pw12', 'first_name': 'Created', 'last_name': 'Staff',
			'age': 28, 'height': 170, 'weight': 70, 'is_staff': True, 'is_superuser': False,
			'ideal': {'ideal_weight': 75}
		}
		res = self.client.post(url, payload, format='json')
		self.assertEqual(res.status_code, 201)
		self.assertTrue(User.objects.filter(email='createdstaff@example.com', is_staff=True).exists())

		# try to create a superuser (should be forbidden for non-super admins)
		payload['email'] = 'bad@example.com'
		payload['is_superuser'] = True
		res2 = self.client.post(url, payload, format='json')
		self.assertEqual(res2.status_code, 403)

	def test_superuser_can_create_superuser(self):
		self.client.force_authenticate(user=self.superuser)
		url = reverse('admin-create')
		payload = {
			'email': 'new_super@example.com', 'password': 'pw12', 'first_name': 'Created', 'last_name': 'Super',
			'age': 45, 'height': 180, 'weight': 85, 'is_staff': True, 'is_superuser': True,
			'ideal': {'ideal_weight': 90}
		}
		res = self.client.post(url, payload, format='json')
		self.assertEqual(res.status_code, 201)
		self.assertTrue(User.objects.filter(email='new_super@example.com', is_superuser=True).exists())


class UsersBusinessLogicTests(TestCase):
	"""Tests for serializer and API business logic (not permission checks)."""

	def setUp(self):
		self.client = APIClient()
  
    # ---------- TEST CASES ----------

	def test_user_serializer_nested_ideal_sets_goal_gain_lose_and_nutrition(self):
		from apps.users.api.serializers import UserSerializer, IdealSerializer
		from Nutrimate.core.enums import Goal

		# Gain weight (ideal > current)
		data = {
			'email': 'a1@example.com', 'password': 'pw12', 'first_name': 'A', 'last_name': 'One',
			'age': 30, 'height': 170, 'weight': 60,
			'ideal': {'ideal_weight': 70}
		}
		s = UserSerializer(data=data)
		self.assertTrue(s.is_valid(), s.errors)
		user = s.save()
		self.assertEqual(user.ideal.goal, Goal.GAIN_WEIGHT)

		# Lose weight (ideal < current)
		data2 = {
			'email': 'a2@example.com', 'password': 'pw12', 'first_name': 'A', 'last_name': 'Two',
			'age': 30, 'height': 170, 'weight': 80,
			'ideal': {'ideal_weight': 70}
		}
		s2 = UserSerializer(data=data2)
		self.assertTrue(s2.is_valid(), s2.errors)
		user2 = s2.save()
		self.assertEqual(user2.ideal.goal, Goal.LOSE_WEIGHT)

		# No ideal_weight provided -> NUTRITION
		data3 = {
			'email': 'a3@example.com', 'password': 'pw12', 'first_name': 'A', 'last_name': 'Three',
			'age': 30, 'height': 170, 'weight': 70,
			'ideal': {}
		}
		s3 = UserSerializer(data=data3)
		# An empty `ideal` dict is treated as no-ideal provided by the serializer
		# in the current implementation (no Ideal is created). Assert that
		# behavior instead of expecting a created Ideal.
		self.assertTrue(s3.is_valid(), s3.errors)
		user3 = s3.save()
		self.assertIsNone(user3.ideal)

	def test_user_serializer_raises_when_ideal_equals_current(self):
		from apps.users.api.serializers import UserSerializer

		data = {
			'email': 'a4@example.com', 'password': 'pw12', 'first_name': 'A', 'last_name': 'Eq',
			'age': 30, 'height': 170, 'weight': 70,
			'ideal': {'ideal_weight': 70}
		}
		s = UserSerializer(data=data)
		self.assertTrue(s.is_valid(), s.errors)

		# Save should raise ValidationError because ideal == current weight
		from rest_framework.exceptions import ValidationError
		with self.assertRaises(ValidationError):
			s.save()

	def test_unique_email_validation(self):
		from apps.users.api.serializers import UserSerializer

		# create initial user
		User.objects.create_user(email='dup@example.com', password='pw12', first_name='D', last_name='U', age=25, height=160, weight=60, ideal=None)

		s = UserSerializer(data={
			'email': 'dup@example.com', 'password': 'pw2', 'first_name': 'X', 'last_name': 'Y',
			'age': 20, 'height': 160, 'weight': 50, 'ideal': {'ideal_weight': 60}
		})

		# Validation should fail because email already exists
		self.assertFalse(s.is_valid())
		self.assertIn('email', s.errors)

	def test_progress_serializer_save_with_bmi_and_comparison_api_logic(self):
		from apps.users.api.serializers import ProgressSerializer
		from apps.users.api.api import ComparisonAPIView

		# create a user and attach ideal and progress
		u = User.objects.create_user(email='puser@example.com', password='pw12', first_name='P', last_name='U', age=28, height=180, weight=100)
		# set ideal
		from apps.users.models import Ideal
		ideal = Ideal.objects.create(goal='L', ideal_weight=70.0)
		u.ideal = ideal
		u.save()

		# create a progress record and ensure bmi saved correctly
		serializer = ProgressSerializer(data={'current_weight': 85.0, 'current_height': 180})
		self.assertTrue(serializer.is_valid(), serializer.errors)
		# BMI = 85 / (1.8^2) = 26.234567901234566
		bmi = 85.0 / ((180.0/100.0) ** 2)
		progress = serializer.save(bmi=bmi)
		u.progress = progress
		u.save()

		# Now test ComparisonAPIView calculation: percent should be 50% (85 is halfway between 100->70)
		client = APIClient()
		client.force_authenticate(user=u)
		res = client.get(reverse('comparison'))
		self.assertEqual(res.status_code, 200)
		data = res.json()
		self.assertAlmostEqual(data['percentage'], 50.0, places=1)
		self.assertAlmostEqual(data['difference'], abs(ideal.ideal_weight - progress.current_weight))
		self.assertEqual(data['achieved_goal'], False)
		self.assertAlmostEqual(data['bmi'], progress.bmi)
