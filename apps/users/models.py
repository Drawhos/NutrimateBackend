from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
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

class User(AbstractBaseUser, PermissionsMixin):
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
        on_delete=models.CASCADE
    )
    
    email_opt_out = models.BooleanField(
        'Email opt-out',
        default=False,
        help_text='Si es True, el usuario no recibirá notificaciones por email'
    )

    # Flags required by Django auth for admin/staff permissions
    is_staff = models.BooleanField(
        'staff status',
        default=False,
        help_text='Designates whether the user can log into this admin site.',
    )

    is_active = models.BooleanField(
        'active',
        default=True,
        help_text='Designates whether this user should be treated as active. '
                  'Unselect this instead of deleting accounts.',
    )
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'age', 'height', 'weight']

    objects = UserManager()

    def __str__(self):
        return self.email

    
class Progress(models.Model):
    bmi = models.FloatField(help_text="Indice de Masa Corporal")
    current_weight = models.FloatField(help_text="Peso actual en kilogramos")
    current_height = models.FloatField(help_text="Altura actual en centímetros")
    last_updated = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Progress recorded on {self.last_updated} with a BMI of {self.bmi}"

class Ideal(models.Model):
    goal = models.CharField(
        max_length=1,
        choices=Goal.choices
    )
    ideal_weight = models.FloatField(help_text="Peso Ideal en kilogramos", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ideal for {self.user.first_name} recorded on {self.created_at}"
