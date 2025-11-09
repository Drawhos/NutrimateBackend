from django.urls import path, include
from rest_framework import routers
from .api.api import UserCreateAPIView, UserLoginAPIView

urlpatterns = [
    path('register/', UserCreateAPIView.as_view(), name='user-create'),
    path('login/', UserLoginAPIView.as_view(), name='user-login'),
]
