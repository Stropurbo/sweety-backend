from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Exists, OuterRef
import cloudinary.uploader
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer
from .models import User
from posts.models import Post, PostMedia, HiddenPost, SavedPost
from posts.serializers import PostSerializer
from posts.views import annotate_posts, PostCursorPagination


class LoginRateThrottle(AnonRateThrottle):
    rate = '5/minute'
    scope = 'login'


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user, context={'request': request}).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user, context={'request': request}).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            token = RefreshToken(request.data.get('refresh'))
            token.blacklist()
        except Exception:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user, context={'request': request}).data)


class AdminStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        users = User.objects.all().order_by('-id')[:50]
        posts = Post.objects.all().order_by('-created_at')[:50]
        return Response({
            'total_users': User.objects.count(),
            'total_posts': Post.objects.count(),
            'public_posts': Post.objects.filter(visibility='public').count(),
            'private_posts': Post.objects.filter(visibility='private').count(),
            'users': UserSerializer(users, many=True, context={'request': request}).data,
            'recent_posts': [{
                'id': p.id,
                'author_id': p.author_id,
                'author': f"{p.author.first_name} {p.author.last_name}",
                'author_email': p.author.email,
                'content': p.content[:80],
                'visibility': p.visibility,
                'likes': p.likes_count,
                'comments': p.comments_count,
                'created_at': p.created_at,
            } for p in posts.select_related('author')],
        })


class AdminDeleteUserView(APIView):
    permission_classes = [IsAdminUser]

    def delete(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            return Response({'error': 'Cannot delete yourself.'}, status=status.HTTP_400_BAD_REQUEST)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminToggleRoleView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            return Response({'error': 'Cannot change your own role.'}, status=status.HTTP_400_BAD_REQUEST)
        user.is_staff = not user.is_staff
        user.save()
        return Response(UserSerializer(user, context={'request': request}).data)


class AdminDeletePostView(APIView):
    permission_classes = [IsAdminUser]

    def delete(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        if len(q) < 1:
            return Response([])
        users = User.objects.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q)
        ).exclude(id=request.user.id)[:10]
        return Response(UserSerializer(users, many=True, context={'request': request}).data)


class SuggestedUsersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from friends.models import Friendship
        friend_ids = Friendship.objects.filter(
            status='accepted'
        ).filter(
            Q(sender=request.user) | Q(receiver=request.user)
        ).values_list('sender_id', 'receiver_id')
        excluded = {request.user.id}
        for s, r in friend_ids:
            excluded.add(s)
            excluded.add(r)
        limit = min(int(request.query_params.get('limit', 6)), 20)
        # use id-based random sampling instead of ORDER BY RANDOM()
        import random
        max_id = User.objects.order_by('-id').values_list('id', flat=True).first() or 0
        candidate_ids = random.sample(range(1, max_id + 1), min(limit * 5, max_id))
        users = User.objects.filter(id__in=candidate_ids).exclude(id__in=excluded)[:limit]
        return Response(UserSerializer(users, many=True, context={'request': request}).data)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if request.user == user:
            base_qs = Post.objects.filter(author=user)
        else:
            base_qs = Post.objects.filter(author=user, visibility='public')
        posts = annotate_posts(base_qs, request.user)
        return Response({
            'user': UserSerializer(user, context={'request': request}).data,
            'posts': PostSerializer(posts, many=True, context={'request': request}).data,
        })


class UpdateProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request):
        user = request.user
        if 'first_name' in request.data:
            user.first_name = request.data['first_name'][:50]
        if 'last_name' in request.data:
            user.last_name = request.data['last_name'][:50]
        if 'bio' in request.data:
            user.bio = request.data['bio'][:500]
        if 'email_visible' in request.data:
            user.email_visible = request.data['email_visible'] in [True, 'true', '1']
        if 'cover_position_y' in request.data:
            try:
                val = float(request.data['cover_position_y'])
                user.cover_position_y = max(0.0, min(100.0, val))
            except (ValueError, TypeError):
                pass
        if 'avatar' in request.FILES:
            res = cloudinary.uploader.upload(request.FILES['avatar'], folder='sweety/avatars')
            user.avatar = res.get('secure_url')
        if 'cover_photo' in request.FILES:
            res = cloudinary.uploader.upload(request.FILES['cover_photo'], folder='sweety/covers')
            user.cover_photo = res.get('secure_url')
        user.save()
        return Response(UserSerializer(user, context={'request': request}).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        current = request.data.get('current_password', '')
        new = request.data.get('new_password', '')
        if not request.user.check_password(current):
            return Response({'error': 'Current password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(new) < 8:
            return Response({'error': 'Password must be at least 8 characters.'}, status=status.HTTP_400_BAD_REQUEST)
        if new.isdigit():
            return Response({'error': 'Password cannot be entirely numeric.'}, status=status.HTTP_400_BAD_REQUEST)
        if new == current:
            return Response({'error': 'New password must differ from current password.'}, status=status.HTTP_400_BAD_REQUEST)
        request.user.set_password(new)
        request.user.save()
        # blacklist all existing refresh tokens by rotating
        return Response({'message': 'Password changed successfully.'})
