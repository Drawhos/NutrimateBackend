from rest_framework import serializers
from apps.users.models import User, Ideal, Progress
from apps.diets.models import Tag
from Nutrimate.core.enums import Goal


class IdealSerializer(serializers.ModelSerializer):
    ideal_weight = serializers.FloatField(required=True, min_value=30, max_value=100)
    goal = serializers.ChoiceField(choices=Ideal._meta.get_field('goal').choices, required=False)
    
    class Meta:
        model = Ideal
        fields = [
            'id',
            'goal',
            'ideal_weight'
        ]
        read_only_fields = ['id','goal','created_at']


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
            if ideal_obj.ideal_weight == user.weight:
                raise serializers.ValidationError({
                'ideal_weight': f'El peso ideal y el peso actual no pueden ser los mismos. Peso elegido: {ideal_obj.ideal_weight}'
                })
            elif ideal_obj.ideal_weight is None:
                ideal_obj.goal = Goal.NUTRITION
            elif ideal_obj.ideal_weight < user.weight:
                ideal_obj.goal = Goal.LOSE_WEIGHT
            else:
                ideal_obj.goal = Goal.GAIN_WEIGHT
            ideal_obj.save()
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


class ProgressSerializer(serializers.ModelSerializer):
    current_weight = serializers.FloatField(required=True, min_value=30, max_value=170)
    current_height = serializers.FloatField(required=True, min_value=60, max_value=270)
    class Meta:
        model = Progress
        fields = [
            'id',
            'bmi',
            'last_updated',
            'current_weight',
            'current_height'
        ]
        read_only_fields = ['id', 'last_updated', 'bmi']


class ComparisonSerializer(serializers.Serializer):
    difference = serializers.FloatField(required=False, min_value=30, max_value=170)
    percentage = serializers.FloatField(required=False, min_value=60, max_value=270)
    achieved_goal = serializers.BooleanField()
    bmi = serializers.FloatField()
