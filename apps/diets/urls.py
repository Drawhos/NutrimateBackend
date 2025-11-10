from django.urls import path
from .api.api import DietCreateAPIView, DietDeleteAPIView, RecipeListCreateAPIView, TagListCreateAPIView, RecipeDeleteAPIView, TagDeleteAPIView


urlpatterns = [
    path('tags/', TagListCreateAPIView.as_view(), name='tag-list-create'),
    path('tags/<int:pk>/', TagDeleteAPIView.as_view(), name='tag-delete'),
    path('recipes/', RecipeListCreateAPIView.as_view(), name='recipe-list-create'),
    path('recipes/<int:pk>/', RecipeDeleteAPIView.as_view(), name='recipe-delete'),
    path('diets/', DietCreateAPIView.as_view(), name='diet-api'),
    path('diets/<int:pk>/', DietDeleteAPIView.as_view(), name='diet-delete')
]
