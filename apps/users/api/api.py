from rest_framework import generics
from .serializers import UserSerializer

class UserCreateAPIView(generics.CreateAPIView):
    serializer_class = UserSerializer