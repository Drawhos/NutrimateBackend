from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token

from apps.diets.models import Diet
from apps.diets.api.serializers import DietDetailedSerializer
from apps.users.models import User

from .serializers import ComparisonSerializer, ProgressSerializer, UserSerializer, LoginSerializer, AdminUserSerializer
from rest_framework.exceptions import PermissionDenied
from django.views.generic import TemplateView


class UserCreateAPIView(generics.CreateAPIView):
    serializer_class = UserSerializer


class AdminCreateAPIView(generics.CreateAPIView):
    """API endpoint to create admin/staff users. Only accessible to admin users.

    - Only requests authenticated as admin (IsAdminUser) can call this endpoint.
    - If the payload attempts to set is_superuser=True, the requester must be a superuser.
    """
    permission_classes = [IsAdminUser]
    serializer_class = AdminUserSerializer

    def perform_create(self, serializer):
        # if trying to create a superuser, require the requester to be superuser
        wanting_super = serializer.validated_data.get('is_superuser', False)
        if wanting_super and not (self.request.user and self.request.user.is_superuser):
            raise PermissionDenied('Only superusers may create superuser accounts')

        # Ensure created admin accounts are active and staff by default if not provided
        serializer.validated_data.setdefault('is_staff', True)
        serializer.validated_data.setdefault('is_active', True)

        # Delegate to normal save
        serializer.save()


class UserGetAPIView(generics.ListAPIView):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    

class UserLoginAPIView(generics.GenericAPIView):
    """Authenticate a user and return an auth token.

    Request body: { "email": "...", "password": "..." }
    Response (200): { "token": "...", "user": { ... } }
    """
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data.get('email')
        password = serializer.validated_data.get('password')

        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response({'detail': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

        token, _ = Token.objects.get_or_create(user=user)
        user_data = UserSerializer(user).data

        return Response({'token': token.key, 'user': user_data}, status=status.HTTP_200_OK)
    

class UserLogoutAPIView(generics.GenericAPIView):
    """Logout a user by deleting their auth token.

    Request header: Authorization: Token <token>
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        Token.objects.filter(user=user).delete()
        return Response({'detail': 'Sesión cerrada exitosamente'}, status=status.HTTP_200_OK)

    
class ProgressCreateAPIView(generics.CreateAPIView):
    """API view to create a user's progress record.

    POST: Create a new progress record.

    Request body (POST): {
        "current_weight": float,
        "current_height": float
    }
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ProgressSerializer

    def post(self, request, *args, **kwargs):
        user = request.user
        if user.progress:
            return Response({'detail': 'El usuario ya tiene un registro de progreso.'}, status=status.HTTP_200_OK)
        
        if user.ideal.goal == 'N':
            return Response({'detail': 'El usuario no tiene como objetivo cambiar su peso'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        current_weight = serializer.validated_data.get('current_weight')
        current_height = serializer.validated_data.get('current_height')
        
        # BMI = weight (kg) / (height (m))^2
        height_in_meters = current_height / 100
        bmi = current_weight / (height_in_meters ** 2)
        
        progress = serializer.save(bmi=bmi)
        user.progress = progress
        user.save()

        return Response(ProgressSerializer(progress).data, status=status.HTTP_201_CREATED)
    
    
class ProgressPatchAPIView(generics.UpdateAPIView):
    """API view to update a user's progress record.

    PATCH: Update an existing progress record.

    Request body (PATCH): {
        "current_weight": float,
        "current_height": float
    }
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ProgressSerializer

    def patch(self, request, *args, **kwargs):
        user = request.user
        progress = user.progress

        if not progress:
            return Response({'detail': 'El usuario no tiene un registro de progreso.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(progress, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        current_weight = serializer.validated_data.get('current_weight')
        current_height = serializer.validated_data.get('current_height')
        
        # Use existing values if not provided in request
        if current_weight is None:
            current_weight = progress.current_weight
        if current_height is None:
            current_height = progress.current_height
        
        height_in_meters = current_height / 100
        bmi = current_weight / (height_in_meters ** 2)
        
        serializer.save(bmi=bmi)

        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
class ComparisonAPIView(generics.GenericAPIView):
    """API view to compare user's progress weight with ideal weight.

    GET: Compare progress weight with ideal weight.
    
    Calculation:
    - Ideal weight = 100%
    - User current weight = 0%
    - Progress weight = percentage to calculate
    - If no progress, percentage is 0%

    Response (GET): {
        "difference": float,
        "percentage": float,
        "achieved_goal": boolean
    }
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ComparisonSerializer

    def get(self, request, *args, **kwargs):
        user = request.user
        ideal = user.ideal

        if not ideal:
            return Response({'detail': 'El usuario no tiene un peso ideal definido.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not ideal.ideal_weight:
            return Response({'detail': 'El usuario no tiene un peso ideal definido.'}, status=status.HTTP_400_BAD_REQUEST)

        progress = user.progress
        progress_weight = progress.current_weight if progress else None
        
        if not progress_weight:
            percentage = 0.0
            difference = ideal.ideal_weight - user.weight
            achieved_goal = False
            bmi = user.weight / ((user.height / 100) ** 2)
        else:
            # Calculate percentage: (progress_weight - user.weight) / (ideal.ideal_weight - user.weight) * 100
            # This represents how much progress has been made towards the goal
            total_range = ideal.ideal_weight - user.weight
            progress_range = progress_weight - user.weight
            
            if total_range == 0:
                # No range to progress through
                percentage = 100.0 if progress_weight == ideal.ideal_weight else 0.0
            else:
                percentage = (progress_range / total_range) * 100
                # Clamp percentage between 0 and 100
                percentage = max(0.0, min(100.0, percentage))
            
            difference = abs(ideal.ideal_weight - progress_weight)
            achieved_goal = (progress_weight == ideal.ideal_weight)
            bmi = progress.bmi

        data = {
            'difference': difference,
            'percentage': percentage,
            'achieved_goal': achieved_goal,
            'bmi': bmi,
        }

        serializer = self.get_serializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GetHistoricalApiView(generics.ListAPIView):
    """API view to retrieve all diets related to the authenticated user's historical.

    GET: Retrieve all diets for the authenticated user.
    
    Optional query parameters:
    - start_date: Filter diets starting from this date (YYYY-MM-DD format)
    - end_date: Filter diets up to this date (YYYY-MM-DD format)

    Response (GET): [
        {
            "id": 1,
            "startDate": "YYYY-MM-DD",
            "endDate": "YYYY-MM-DD",
            "menus": [...]
        },
        ...
    ]
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DietDetailedSerializer

    def get_queryset(self):
        from datetime import datetime
        
        user = self.request.user
        diets = Diet.objects.filter(user=user)
        
        # Apply date range filters if provided
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                diets = diets.filter(startDate__gte=start_date_obj)
            except ValueError:
                pass  # Invalid format, ignore the filter
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                diets = diets.filter(endDate__lte=end_date_obj)
            except ValueError:
                pass  # Invalid format, ignore the filter
        
        return diets


class UnsubscribeByCredentialsAPIView(generics.GenericAPIView):
    """Public API endpoint that unsubscribes a user when they provide email + password.

    POST body: { "email": "..", "password": ".." }
    Response: 200 OK or 401 on bad credentials.
    """
    permission_classes = []  # allow public
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data.get('email')
        password = serializer.validated_data.get('password')

        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response({'detail': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

        if user.email_opt_out:
            return Response({'detail': 'Usuario ya desuscrito.'}, status=status.HTTP_200_OK)

        user.email_opt_out = True
        user.save(update_fields=['email_opt_out'])

        return Response({'detail': 'Desuscrito con éxito.'}, status=status.HTTP_200_OK)


class UnsubscribeFormView(TemplateView):
    """Simple public HTML form where users can enter email + password to unsubscribe.

    This page posts to the API endpoint implemented above.
    """
    template_name = 'unsubscribe/unsubscribe_form.html'
