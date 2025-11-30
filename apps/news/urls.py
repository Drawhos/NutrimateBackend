from django.urls import path
from .api.api import NewsListAPIView


urlpatterns = [
    path('news/', NewsListAPIView.as_view(), name='news-list')
]