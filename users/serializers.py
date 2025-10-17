from rest_framework import serializers
from models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'age', 'height', 'weight', 'first_name', 'last_name', 'date_joined')
        read_only_fields = ('id', 'date_joined',)
        

