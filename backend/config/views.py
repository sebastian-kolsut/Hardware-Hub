from django.contrib.auth import authenticate
from rest_framework import generics
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import IsAdminUser
from .serializers import UserCreateSerializer


@api_view(['GET'])
def ping(request):
    return Response({'status': 'ok'})


class LoginView(APIView):
    """Exchanges username+password for an auth token."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        if not username or not password:
            return Response(
                {'detail': 'username and password are required.'}, status=400
            )

        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response({'detail': 'Invalid credentials.'}, status=401)

        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'is_staff': user.is_staff})


class LogoutView(APIView):
    """Deletes the caller's token so it stops working immediately."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        return Response(status=204)


class MeView(APIView):
    """Lets the frontend restore session state from a stored token."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {'username': request.user.username, 'is_staff': request.user.is_staff}
        )


class UserCreateView(generics.CreateAPIView):
    """Admin-only account creation. There is no public registration."""

    permission_classes = [IsAdminUser]
    serializer_class = UserCreateSerializer
