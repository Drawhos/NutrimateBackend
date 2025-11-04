from django.db import models
from Nutrimate.core.enums import Goal

class Diet(models.Model):
    startDate = models.DateField(auto_now_add=True)
    endDate = models.DateField()
    recipes = models.ManyToManyField(
        'diets.Recipe',
        related_name='diets',
        blank=True,
    )
    def __str__(self):
        return f"Diet from {self.startDate} to {self.endDate}"

class Meal(models.TextChoices):
    BREAKFAST = 'B', 'Breakfast'
    LUNCH = 'L', 'Lunch'
    DINNER = 'D', 'Dinner'

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Recipe(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    ingredients = models.JSONField(default=list, blank=True)
    preparation_steps = models.TextField(max_length=255)
    nutritional_info = models.JSONField(default=dict, blank=True)
    meal = models.CharField(
        max_length=1,
        choices=Meal.choices
    )
    goal = models.CharField(
        max_length=1,
        choices=Goal.choices,
        default=Goal.NUTRITION
    )
    tag = models.ManyToManyField(
        'diets.Tag',
        related_name='recipes',
        blank=True,
    )

    def __str__(self):
        return self.name