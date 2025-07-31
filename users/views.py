# users/views.py
from rest_framework import generics, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from accounts.models import User
from .serializers import UserProfileSerializer

class UserProfileView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user
