from rest_framework import routers
from api import UserViewSet

router = routers.DefaultRouter()

router.register('api/users', UserViewSet, 'users')

urlpatterns = router.urls # Igual exportar las URLs generadas por el router
