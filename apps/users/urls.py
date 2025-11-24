from django.urls import path
from .api.api import (
    ProgressCreateAPIView, ProgressPatchAPIView, UserCreateAPIView,
    UserGetAPIView, UserLoginAPIView, UserLogoutAPIView,
    ComparisonAPIView, GetHistoricalApiView, UnsubscribeByCredentialsAPIView,
    UnsubscribeFormView
)


urlpatterns = [
    path('register/', UserCreateAPIView.as_view(), name='user-create'),
    path('login/', UserLoginAPIView.as_view(), name='user-login'),
    path('logout/', UserLogoutAPIView.as_view(), name='user-logout'),
    path('progress/', ProgressCreateAPIView.as_view(), name='progress-create'),
    path('progress/patch/', ProgressPatchAPIView.as_view(), name='progress-patch'),
    path('comparison/', ComparisonAPIView.as_view(), name='comparison'),
    path('historical/', GetHistoricalApiView.as_view(), name='historical-diets'),
    path('unsubscribe/form/', UnsubscribeFormView.as_view(), name='unsubscribe-form'),
    path('unsubscribe-by-credentials/', UnsubscribeByCredentialsAPIView.as_view(), name='unsubscribe-by-credentials'),
    path('getfuckingusers/', UserGetAPIView.as_view(), name='user-get'),
]
