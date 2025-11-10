from django.db import models
from Nutrimate.core.enums import Goal

class Diet(models.Model):
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='diets',
        null=True
    )
    startDate = models.DateField(auto_now_add=True)
    endDate = models.DateField()
    menus = models.ManyToManyField(
        'diets.Menu',
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
    preparation_steps = models.TextField(max_length=500)
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
    tags = models.ManyToManyField(
        'diets.Tag',
        related_name='recipes',
        blank=True,
    )

    def __str__(self):
        return self.name
    
class Menu(models.Model):
    day = models.IntegerField()
    recipes = models.ManyToManyField(
        'diets.Recipe',
        related_name='meals',
        blank=True
    )
    