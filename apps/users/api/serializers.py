from rest_framework import serializers
from apps.users.models import User, Ideal, Progress
from apps.diets.models import Tag
from Nutrimate.core.enums import Goal


class IdealSerializer(serializers.ModelSerializer):
    ideal_weight = serializers.FloatField(required=False, min_value=30, max_value=100)
    goal = serializers.ChoiceField(choices=Ideal._meta.get_field('goal').choices, required=True)
    
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
    
    def validate_email(self, value):
        """Validate that the email does not already exist."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Un usuario con este correo electrónico ya existe.")
        return value
    
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
    ideal = IdealSerializer(required=True)

    def validate(self, data):
        """Validate that ideal_weight is different from current weight before creating."""
        ideal_data = data.get('ideal')
        weight = data.get('weight')
        
        if ideal_data and ideal_data.get('ideal_weight'):
            if ideal_data.get('ideal_weight') == weight:
                raise serializers.ValidationError({
                    'ideal': f'El peso ideal y el peso actual no pueden ser los mismos. Peso elegido: {ideal_data.get("ideal_weight")}'
                })
        
        return data

    def create(self, validated_data):
        ideal_data = validated_data.pop('ideal', None)
        user = super().create(validated_data)

        password = validated_data.get('password') or None
        if password:
            user.set_password(password)
            user.save()

        if ideal_data:
            ideal_obj = Ideal.objects.create(**ideal_data)
            
            # Set goal based on ideal_weight
            if ideal_obj.ideal_weight is None:
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
            'email_opt_out',
            'is_staff',
            'is_superuser'
        ]
        read_only_fields = ['id','date_joined', 'email_opt_out']


class AdminUserSerializer(UserSerializer):
    """Serializer used by admin-only API to create admin/staff users.

    This exposes `is_staff` and `is_superuser` so an admin can create staff or other admin accounts.
    The view must enforce who is allowed to set `is_superuser`.
    """
    is_staff = serializers.BooleanField(required=False, default=True)
    is_superuser = serializers.BooleanField(required=False, default=False)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ['is_staff', 'is_superuser']


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


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer to validate old password and new password for authenticated users."""
    old_password = serializers.CharField(write_only=True, required=True, min_length=4)
    new_password = serializers.CharField(write_only=True, required=True, min_length=4)
    confirm_password = serializers.CharField(write_only=True, required=True, min_length=4)

    def validate(self, data):
        """Validate that new_password and confirm_password match."""
        if data.get('new_password') != data.get('confirm_password'):
            raise serializers.ValidationError({'confirm_password': 'Las contraseñas no coinciden.'})
        
        if data.get('old_password') == data.get('new_password'):
            raise serializers.ValidationError({'new_password': 'La nueva contraseña debe ser diferente a la anterior.'})
        
        return data
