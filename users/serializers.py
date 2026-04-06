from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'password']

    def validate_password(self, value):
        if value.isdigit():
            raise serializers.ValidationError('Password cannot be entirely numeric.')
        if value.lower() in ('password', '12345678', 'qwerty123'):
            raise serializers.ValidationError('Password is too common.')
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError('Invalid email or password.')
        if not user.is_active:
            raise serializers.ValidationError('This account has been deactivated.')
        data['user'] = user
        return data


class UserSerializer(serializers.ModelSerializer):
    post_count = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'email', 'is_staff',
            'bio', 'avatar', 'cover_photo', 'cover_position_y',
            'email_visible', 'created_at', 'post_count', 'is_online',
        ]

    def get_email(self, obj):
        request = self.context.get('request')
        # show email only to the owner or staff
        if request and (request.user == obj or request.user.is_staff):
            return obj.email
        if obj.email_visible:
            return obj.email
        return None

    def get_post_count(self, obj):
        # use annotated value if available (avoids extra query)
        return getattr(obj, 'post_count_annotated', None) or obj.posts.count()

    def get_is_online(self, obj):
        if not obj.last_seen:
            return False
        return (timezone.now() - obj.last_seen).total_seconds() < 300
