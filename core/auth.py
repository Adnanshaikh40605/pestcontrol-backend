import logging
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.throttling import AnonRateThrottle
from django.contrib.auth import authenticate
from rest_framework import serializers

logger = logging.getLogger(__name__)


class LoginRateThrottle(AnonRateThrottle):
    """Custom throttle for login attempts."""
    scope = 'login'


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Enhanced JWT token serializer with additional user information."""
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['user_id'] = user.id
        token['username'] = user.username
        token['email'] = user.email
        token['is_staff'] = user.is_staff
        token['is_superuser'] = user.is_superuser
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        return token

    def validate(self, attrs):
        """Enhanced validation with logging and additional checks."""
        username = attrs.get('username')
        password = attrs.get('password')
        
        if not username or not password:
            raise serializers.ValidationError('Username and password are required.')
        
        # Log login attempt
        logger.info(f"Login attempt for username: {username}")
        
        # Authenticate user
        user = authenticate(username=username, password=password)
        if user is None:
            logger.warning(f"Failed login attempt for username: {username}")
            raise serializers.ValidationError('Invalid credentials.')
        
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {username}")
            raise serializers.ValidationError('User account is disabled.')
        
        data = super().validate(attrs)
        
        # Add additional user information to response
        data.update({
            'user_id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'is_staff': self.user.is_staff,
            'is_superuser': self.user.is_superuser,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
        })
        
        logger.info(f"Successful login for user: {username}")
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    """Enhanced JWT token view with throttling."""
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]
    
    def post(self, request, *args, **kwargs):
        """Override post to add additional logging."""
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            logger.info(f"Successful token generation for user: {request.data.get('username')}")
        else:
            logger.warning(f"Failed token generation attempt: {response.status_code}")
        return response


