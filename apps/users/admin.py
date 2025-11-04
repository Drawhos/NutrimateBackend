from django.contrib import admin
from .models import User, Historical, Progress, Ideal

admin.site.register(User)
admin.site.register(Historical)
admin.site.register(Progress)
admin.site.register(Ideal)
