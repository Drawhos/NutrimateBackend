from django.urls import path, include
from rest_framework import routers
from .api.api import UserCreateAPIView

urlpatterns = [
    path('', UserCreateAPIView.as_view(), name='user-create'),
]
