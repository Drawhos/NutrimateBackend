from django.db import models

class Goal(models.TextChoices):
    GAIN_WEIGHT = 'G', 'Gain Weight'
    LOSE_WEIGHT = 'L', 'Lose Weight'
    NUTRITION = 'N', 'Nutrition'