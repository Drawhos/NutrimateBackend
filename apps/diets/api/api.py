from rest_framework import generics, status, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.diets.models import Diet, Tag, Recipe

from .serializers import DietSerializer, RecipeSerializer, TagSerializer


class TagListCreateAPIView(generics.ListCreateAPIView):
    """List all tags or create a new tag.

    GET: List all tags.
    POST: Create a new tag or multiple tags.

    Request body (POST): { "name": "...", "description": "..." }
    Response (GET): [ { "id": 1, "name": "...", "description": "..." }, ... ]
    Response (POST): { "id": 1, "name": "...", "description": "..." }
    """
    serializer_class = TagSerializer
    queryset = Tag.objects.all()
    
    def get_serializer(self, *args, **kwargs):
        """
        Si los datos son una lista, pasa many=True para habilitar la creación masiva
        """
        if isinstance(kwargs.get('data', {}), list):
            kwargs['many'] = True
        return super().get_serializer(*args, **kwargs)


class TagDeleteAPIView(generics.DestroyAPIView):
    """API view to delete a tag.

    DELETE: Delete a tag by ID.

    Response (DELETE): 204 No Content
    """
    queryset = Tag.objects.all()


class RecipeListCreateAPIView(generics.ListCreateAPIView):
    """List all recipes or create a new recipe.

    GET: List all recipes.
    POST: Create a new recipe or multiple recipes.

    Request body for single recipe (POST):
    {
        "name": "...",
        "description": "...",
        "ingredients": [...],
        "preparation_steps": "...",
        "nutritional_info": {...},
        "meal": "B|L|D",
        "goal": "N|W|L",
        "tag": [tag_id1, tag_id2, ...]
    }

    Request body for multiple recipes (POST):
    [
        {
            "name": "Recipe 1",
            ...
        },
        {
            "name": "Recipe 2",
            ...
        }
    ]

    Response (GET): List of recipe objects
    Response (POST): Created recipe object(s)
    """
    serializer_class = RecipeSerializer
    queryset = Recipe.objects.all()

    def get_serializer(self, *args, **kwargs):
        """
        Si los datos son una lista, pasa many=True para habilitar la creación masiva
        """
        if isinstance(kwargs.get('data', {}), list):
            kwargs['many'] = True
        return super().get_serializer(*args, **kwargs)


class RecipeDeleteAPIView(generics.DestroyAPIView):
    """API view to delete a recipe.

    DELETE: Delete a recipe by ID.

    Response (DELETE): 204 No Content
    """
    queryset = Recipe.objects.all()


class DietCreateAPIView(generics.CreateAPIView):
    """API view for Diet model.

    POST: Create a new diet. Requires authentication.

    Request body (POST): {"recipes": [recipe_id1, recipe_id2, ...] }
    Response (POST): { "id": 1, "startDate": "YYYY-MM-DD", "endDate": "YYYY-MM-DD", "recipes": [recipe_id1, recipe_id2, ...], "user": user_id }
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DietSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    
class DietDeleteAPIView(generics.DestroyAPIView):
    """API view to delete a diet.

    DELETE: Delete a diet by ID.

    Response (DELETE): 204 No Content
    """
    queryset = Diet.objects.all()
