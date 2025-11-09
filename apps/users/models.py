from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from Nutrimate.core.enums import Goal

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El usuario debe tener un correo electrónico')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser):
    email = models.EmailField('Correo electrónico', max_length=255, unique=True)
    age = models.PositiveSmallIntegerField()
    height = models.FloatField(help_text="Altura en centímetros")
    weight = models.FloatField(help_text="Peso en kilogramos")
    first_name = models.TextField(max_length=30)
    last_name = models.TextField(max_length=30)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    ## Uno a Uno
    progress = models.OneToOneField(
        'Progress',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    tags = models.ManyToManyField(
        'diets.Tag',
        related_name='users',
        blank=True,
    )
    
    ideal = models.OneToOneField(
        'Ideal',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'age', 'height', 'weight']

    objects = UserManager()

    def __str__(self):
        return self.email

class Historical(models.Model):
    # uno a muchos
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='historicals'
    )
    diets = models.ManyToManyField(
        'diets.Diet',
        related_name='historical_diets',
        blank=True,
    )
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.activity} on {self.date}" ##
    
class Progress(models.Model):
    bmi = models.FloatField(help_text="Indice de Masa Corporal")
    date_recorded = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Progress recorded on {self.date_recorded} with a BMI of {self.bmi}"

class Ideal(models.Model):
    goal = models.CharField(
        max_length=1,
        choices=Goal.choices,
        default=Goal.NUTRITION
    )
    ideal_weight = models.FloatField(help_text="Peso Ideal en kilogramos", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ideal for {self.user.username} recorded on {self.created_at}"