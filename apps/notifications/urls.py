from django.urls import path
from .api.api import EmailAPIView


urlpatterns = [
    path('email-notification/', EmailAPIView.as_view(), name='email-notification')
]