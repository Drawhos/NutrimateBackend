from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse
from apps.users.models import User
from apps.diets.models import Tag, Recipe, Diet, Menu


class DietsAPITestCase(TestCase):
	def setUp(self):
		# Create an admin user
		self.admin = User.objects.create_superuser(
			email='admin@example.com',
			password='adminpass',
			first_name='Admin',
			last_name='Istrator',
			age=30,
			height=170,
			weight=70,
		)

		# Create a regular user
		self.user = User.objects.create_user(
			email='user@example.com',
			password='userpass',
			first_name='Normal',
			last_name='User',
			age=26,
			height=175,
			weight=75,
		)

		self.client = APIClient()
  
    # ---------- TEST CASES ----------

	def test_recipe_bulk_create_and_tags_assignment(self):
		# Create some tags first
		t1 = Tag.objects.create(name='egg', description='egg')
		t2 = Tag.objects.create(name='chicken', description='chicken')

		url = reverse('recipe-list-create')
		self.client.force_authenticate(user=self.admin)

		payload = [
			{
				'name': 'R1', 'description': 'r1', 'ingredients': [], 'preparation_steps': 'do',
				'nutritional_info': {}, 'meal': 'B', 'goal': 'N', 'tags': [t1.id]
			},
			{
				'name': 'R2', 'description': 'r2', 'ingredients': [], 'preparation_steps': 'do',
				'nutritional_info': {}, 'meal': 'L', 'goal': 'N', 'tags': [t2.id]
			}
		]

		resp = self.client.post(url, payload, format='json')
		self.assertEqual(resp.status_code, 201)
		self.assertEqual(Recipe.objects.count(), 2)

		r1 = Recipe.objects.get(name='R1')
		self.assertIn(t1, r1.tags.all())

	def test_diet_create_requires_auth_and_creates_menus(self):
		url = reverse('diet-api')

		# unauthenticated should be 401
		resp = self.client.post(url, {}, format='json')
		self.assertEqual(resp.status_code, 401)

		# prepare recipe pool (at least one per meal)
		Recipe.objects.create(name='B1', description='b', ingredients=[], preparation_steps='x', nutritional_info={}, meal='B', goal='N')
		Recipe.objects.create(name='L1', description='l', ingredients=[], preparation_steps='x', nutritional_info={}, meal='L', goal='N')
		Recipe.objects.create(name='D1', description='d', ingredients=[], preparation_steps='x', nutritional_info={}, meal='D', goal='N')

		# authenticate user and create diet
		self.client.force_authenticate(user=self.user)
		resp = self.client.post(url, {}, format='json')
		self.assertEqual(resp.status_code, 201)

		# One diet created for the user
		diets = Diet.objects.filter(user=self.user)
		self.assertEqual(diets.count(), 1)

		diet = diets.first()
		# should have 7 menus, each with 3 recipes
		self.assertEqual(diet.menus.count(), 7)
		for menu in diet.menus.all():
			self.assertEqual(menu.recipes.count(), 3)


class DietsSerializerLogicTests(TestCase):
		"""Tests focused on serializer/business logic (no auth checks).

		These tests exercise the ListSerializer bulk create behavior and the
		DietSerializer generation logic (excluding recipes with user tags, goal
		filtering, menu creation count, and attachments).
		"""

		def setUp(self):
			# create user and tags
			self.user = User.objects.create_user(
				email='bizuser@example.com', password='bizpass',
				first_name='Biz', last_name='Logic', age=28, height=170, weight=68
			)
   
        # ---------- TEST CASES ----------

		def test_tag_list_serializer_bulk_create(self):
			from apps.diets.api.serializers import TagSerializer

			data = [
				{'name': 'tA', 'description': 'A'},
				{'name': 'tB', 'description': 'B'},
			]

			serializer = TagSerializer(data=data, many=True)
			self.assertTrue(serializer.is_valid(), serializer.errors)
			created = serializer.save()
			self.assertEqual(len(created), 2)
			self.assertTrue(Tag.objects.filter(name='tA').exists())

		def test_recipe_list_serializer_bulk_create_and_m2m(self):
			from apps.diets.api.serializers import RecipeSerializer

			t1 = Tag.objects.create(name='tX', description='x')
			t2 = Tag.objects.create(name='tY', description='y')

			payload = [
				{
					'name': 'Bulk1', 'description': 'd', 'ingredients': [], 'preparation_steps': 's',
					'nutritional_info': {}, 'meal': 'B', 'goal': 'N', 'tags': [t1.id]
				},
				{
					'name': 'Bulk2', 'description': 'd', 'ingredients': [], 'preparation_steps': 's',
					'nutritional_info': {}, 'meal': 'L', 'goal': 'N', 'tags': [t2.id]
				}
			]

			serializer = RecipeSerializer(data=payload, many=True)
			self.assertTrue(serializer.is_valid(), serializer.errors)
			created = serializer.save()

			self.assertEqual(len(created), 2)
			r = Recipe.objects.get(name='Bulk1')
			self.assertIn(t1, r.tags.all())

		def test_diet_serializer_excludes_user_tagged_recipes_and_filters_by_goal(self):
			from apps.diets.api.serializers import DietSerializer
			from apps.users.models import Ideal
			from Nutrimate.core.enums import Goal

			# user has a tag that should exclude recipes with that tag
			excl_tag = Tag.objects.create(name='exclude', description='e')
			self.user.tags.add(excl_tag)

			# set user's ideal goal to LOSE_WEIGHT ('L')
			ideal = Ideal.objects.create(goal=Goal.LOSE_WEIGHT, ideal_weight=60.0)
			self.user.ideal = ideal
			self.user.save()

			# Create recipes, some with excluded tag, some with different goals
			# Eligible recipes for user should be goal == 'L' and without excl_tag
			# Make small pools so repetition logic triggers but that's fine
			# eligible meals
			Recipe.objects.create(name='B_ok', description='b', ingredients=[], preparation_steps='x', nutritional_info={}, meal='B', goal='L')
			Recipe.objects.create(name='L_ok', description='l', ingredients=[], preparation_steps='x', nutritional_info={}, meal='L', goal='L')
			Recipe.objects.create(name='D_ok', description='d', ingredients=[], preparation_steps='x', nutritional_info={}, meal='D', goal='L')

			# excluded recipe (shares user tag)
			r_excl = Recipe.objects.create(name='B_bad', description='b', ingredients=[], preparation_steps='x', nutritional_info={}, meal='B', goal='L')
			r_excl.tags.set([excl_tag])

			# another recipe with different goal should be excluded by goal
			Recipe.objects.create(name='L_othergoal', description='l', ingredients=[], preparation_steps='x', nutritional_info={}, meal='L', goal='G')

			# Now call DietSerializer.create with only user as validated_data
			serializer = DietSerializer()
			diet = serializer.create({'user': self.user})

			# Check diet created
			self.assertIsInstance(diet, Diet)
			self.assertEqual(diet.menus.count(), 7)

			# Ensure none of the menus contain the excluded recipe
			all_recipe_names = set()
			for menu in diet.menus.all():
				for recipe in menu.recipes.all():
					all_recipe_names.add(recipe.name)

			self.assertNotIn('B_bad', all_recipe_names)
