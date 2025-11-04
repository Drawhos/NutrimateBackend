from rest_framework import serializers
from apps.users.models import User, Ideal
from apps.diets.models import Tag


class UserSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True, max_length=30)
    last_name = serializers.CharField(required=False, max_length=30)
    age = serializers.IntegerField(required=True, min_value=1)
    email = serializers.EmailField(required=True)
    height = serializers.FloatField(required=True, min_value=60, max_value=270)
    weight = serializers.FloatField(required=True, min_value=30, max_value=170) 
    
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        required=False
    )
    progress = serializers.PrimaryKeyRelatedField(
        required=False,
        allow_null=True,
        read_only=True
    )
    ideal = serializers.PrimaryKeyRelatedField(
        queryset=Ideal.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'age',
            'height',
            'weight',
            'date_joined',
            'progress',
            'tags',
            'ideal',
        ]
        read_only_fields = ['id','date_joined']


