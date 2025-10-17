from django.db import models

# Create your models here.
class User(models.Model):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    age = models.PositiveSmallIntegerField()
    height = models.FloatField(help_text="Height in centimeters")
    weight = models.FloatField(help_text="Weight in kilograms")
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username