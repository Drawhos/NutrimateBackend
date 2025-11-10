from rest_framework import serializers
from apps.diets.models import Tag, Recipe, Diet, Menu


class RecipeListSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        m2m_data = []
        recipes = []
        for item in validated_data:
            tags = item.pop('tags', [])
            recipes.append(Recipe(**item))
            m2m_data.append(tags)
        recipes = Recipe.objects.bulk_create(recipes)
        
        for recipe, tag in zip(recipes, m2m_data):
            recipe.tags.set(tag)
        return recipes


class TagListSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        # Create Tag instances in bulk for efficiency
        tags = [Tag(**item) for item in validated_data]
        return Tag.objects.bulk_create(tags)


class TagSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True, max_length=50)
    description = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = Tag
        fields = [
            'id',
            'name',
            'description'
        ]
        read_only_fields = ['id']
        list_serializer_class = TagListSerializer
        
        
class RecipeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True, max_length=100)
    description = serializers.CharField(required=True)
    ingredients = serializers.JSONField(required=True)
    preparation_steps = serializers.CharField(required=True, max_length=500)
    nutritional_info = serializers.JSONField(required=True)
    meal = serializers.ChoiceField(choices=Recipe._meta.get_field('meal').choices, required=True)
    goal = serializers.ChoiceField(choices=Recipe._meta.get_field('goal').choices, required=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        required=True
    )

    class Meta:
        model = Recipe
        fields = [
            'id',
            'name',
            'description',
            'ingredients',
            'preparation_steps',
            'nutritional_info',
            'meal',
            'goal',
            'tags'
        ]
        read_only_fields = ['id']
        list_serializer_class = RecipeListSerializer


class MenuSerializer(serializers.ModelSerializer):
    day = serializers.IntegerField(required=False, min_value=1, max_value=7)
    recipes = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Recipe.objects.all(),
        required=False
    )

    class Meta:
        model = Menu
        fields = [
            'id',
            'day',
            'recipes'
        ]
        read_only_fields = ['id']


class DietSerializer(serializers.ModelSerializer):
    startDate = serializers.DateField(required=False)
    endDate = serializers.DateField(read_only=True)
    # Return fully-formed menus (day + recipe ids) instead of just PKs
    menus = MenuSerializer(many=True, read_only=True)
    
    def create(self, validated_data):
        from datetime import timedelta
        from django.utils import timezone
        import random

        user = validated_data['user']

        if 'startDate' not in validated_data:
            start_date = timezone.now().date()
        else:
            start_date = validated_data['startDate']

        # Calculate endDate (one week later)
        end_date = start_date + timedelta(days=7)

        validated_data['endDate'] = end_date
        validated_data['user'] = user
       
        user_goal = user.ideal.goal if user.ideal else None
        
        # exclude recipes that have at least one tag in common with the user
        user_tags = user.tags.all()
        eligible_qs = Recipe.objects.exclude(tags__in=user_tags).distinct()
        
        # Filter by user's goal if they have one
        if user_goal:
            eligible_qs = eligible_qs.filter(goal=user_goal)

        # Separate recipes by meal type
        breakfasts = list(eligible_qs.filter(meal='B'))
        lunches = list(eligible_qs.filter(meal='L'))
        dinners = list(eligible_qs.filter(meal='D'))

        random.shuffle(breakfasts)
        random.shuffle(lunches)
        random.shuffle(dinners)

        # Create backup lists for repetition if needed
        breakfasts_backup = breakfasts.copy()
        lunches_backup = lunches.copy()
        dinners_backup = dinners.copy()

        # Build list of 21 recipes (3 per day for 7 days)
        result_recipes = []

        for i in range(7):
            # Use item from original pool
            if breakfasts:
                result_recipes.append(breakfasts.pop())
            # If original pool is empty, can reuse from backup
            # Pick a random item from backup (don't remove, allow repetition)
            elif breakfasts_backup:
                result_recipes.append(random.choice(breakfasts_backup))

            # Lunch
            if lunches:
                result_recipes.append(lunches.pop())
            elif lunches_backup:
                result_recipes.append(random.choice(lunches_backup))

            # Dinner
            if dinners:
                result_recipes.append(dinners.pop())
            elif dinners_backup:
                result_recipes.append(random.choice(dinners_backup))

        # Create 7 Menu instances (one per day)
        menu_instances = []
        for day_idx in range(7):
            day_recipes = result_recipes[day_idx*3:(day_idx+1)*3]
            menu = Menu.objects.create(day=day_idx + 1)
            # set m2m recipes for the menu
            menu.recipes.set(day_recipes)
            menu_instances.append(menu)

        # Remove menus from validated_data before creating Diet via super()
        data_for_diet = dict(validated_data)
        if 'menus' in data_for_diet:
            data_for_diet.pop('menus')

        # Create the Diet instancee, then attach menus
        diet = super().create(data_for_diet)
        diet.menus.set(menu_instances)

        return diet
    
    class Meta:
        model = Diet
        fields = [
            'id',
            'startDate',
            'endDate',
            'menus'
        ]
        read_only_fields = ['id', 'menus', 'startDate', 'endDate']
