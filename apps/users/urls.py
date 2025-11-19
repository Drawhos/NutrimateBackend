from django.urls import path
from .api.api import ProgressCreateAPIView, ProgressPatchAPIView, UserCreateAPIView, UserLoginAPIView, UserLogoutAPIView, comparisonAPIView, GetHistoricalApiView


urlpatterns = [
    path('register/', UserCreateAPIView.as_view(), name='user-create'),
    path('login/', UserLoginAPIView.as_view(), name='user-login'),
    path('logout/', UserLogoutAPIView.as_view(), name='user-logout'),
    path('progress/', ProgressCreateAPIView.as_view(), name='progress-create'),
    path('progress/patch/', ProgressPatchAPIView.as_view(), name='progress-patch'),
    path('comparison/', comparisonAPIView.as_view(), name='comparison'),
    path('historical/', GetHistoricalApiView.as_view(), name='historical-diets'),
]
