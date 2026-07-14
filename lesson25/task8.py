# api/views.py
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class ProtectedUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'username': request.user.username})


# config/urls.py
from django.contrib import admin
from django.urls import include, path

from api.views import ProtectedUserView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
    path('api/protected/', ProtectedUserView.as_view(), name='protected-user'),
]


"""
Test w Postmanie bez tokenu:
- metoda: GET
- adres: http://127.0.0.1:8000/api/protected/
- bez ustawionej autoryzacji

Odpowiedź: 401 Unauthorized
{
  "detail": "Authentication credentials were not provided."
}

Test w Postmanie z tokenem:
- metoda: GET
- adres: http://127.0.0.1:8000/api/protected/
- Authorization: Bearer Token
- Token: <access_token>

Odpowiedź: 200 OK
{
  "username": "student1"
}
"""
