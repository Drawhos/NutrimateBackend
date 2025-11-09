from rest_framework import serializers
from apps.users.models import User, Ideal
from apps.diets.models import Tag


class IdealSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ideal
        fields = [
            'id',
            'goal',
            'ideal_weight'
        ]
        read_only_fields = ['id','created_at']


class UserSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True, max_length=30)
    last_name = serializers.CharField(required=False, max_length=30)
    age = serializers.IntegerField(required=True, min_value=1)
    email = serializers.EmailField(required=True)
    height = serializers.FloatField(required=True, min_value=60, max_value=270)
    weight = serializers.FloatField(required=True, min_value=30, max_value=170)
    password = serializers.CharField(write_only=True, required=True, min_length=4)
    
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
    ideal = IdealSerializer(required=False, allow_null=True)

    def create(self, validated_data):
        ideal_data = validated_data.pop('ideal', None)
        user = super().create(validated_data)

        password = validated_data.get('password') or None
        if password:
            user.set_password(password)
            user.save()

        if ideal_data:
            ideal_obj = Ideal.objects.create(**ideal_data)
            user.ideal = ideal_obj
            user.save()

        return user

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
            'password',
            'date_joined',
            'progress',
            'tags',
            'ideal',
        ]
        read_only_fields = ['id','date_joined']

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    