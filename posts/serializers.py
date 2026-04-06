from rest_framework import serializers
from .models import Post, PostMedia, Comment, Reply, Story, HiddenPost, SavedPost, EventInterest, Reaction
from users.serializers import UserSerializer


class StorySerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Story
        fields = ['id', 'author', 'image', 'text', 'bg_color', 'created_at', 'expires_at', 'is_active']


class PostMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostMedia
        fields = ['id', 'url', 'media_type', 'order']


class ReplySerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    likes_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    liked_by = serializers.SerializerMethodField()

    class Meta:
        model = Reply
        fields = ['id', 'author', 'content', 'likes_count', 'is_liked', 'liked_by', 'created_at']

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False

    def get_liked_by(self, obj):
        return UserSerializer(obj.likes.all(), many=True).data


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    replies = ReplySerializer(many=True, read_only=True)
    likes_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    liked_by = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'author', 'content', 'replies', 'likes_count', 'is_liked', 'liked_by', 'created_at']

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False

    def get_liked_by(self, obj):
        return UserSerializer(obj.likes.all(), many=True).data


class PostSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    image = serializers.URLField(required=False, allow_blank=True, allow_null=True, read_only=True)
    video = serializers.URLField(required=False, allow_blank=True, allow_null=True, read_only=True)
    media = PostMediaSerializer(many=True, read_only=True)
    content = serializers.CharField(required=False, allow_blank=True, default='')
    comments = CommentSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    is_liked = serializers.SerializerMethodField()
    liked_by = serializers.SerializerMethodField()
    is_hidden = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()
    interest_count = serializers.SerializerMethodField()
    is_interested = serializers.SerializerMethodField()
    my_reaction = serializers.SerializerMethodField()
    reaction_summary = serializers.SerializerMethodField()

    def validate(self, data):
        request = self.context.get('request')
        has_file = request and (request.FILES.getlist('images') or request.FILES.getlist('videos') or
                                request.FILES.get('image') or request.FILES.get('video'))
        if not data.get('content', '').strip() and not has_file:
            raise serializers.ValidationError('Post must have text or media.')
        return data

    class Meta:
        model = Post
        fields = ['id', 'author', 'post_type', 'content', 'image', 'video', 'media', 'visibility',
                  'event_title', 'event_date', 'event_location',
                  'article_title',
                  'comments', 'likes_count', 'is_liked', 'liked_by', 'is_hidden', 'is_saved',
                  'interest_count', 'is_interested',
                  'my_reaction', 'reaction_summary', 'created_at']

    def get_is_liked(self, obj):
        return getattr(obj, 'is_liked_by_user', False)

    def get_liked_by(self, obj):
        return UserSerializer(obj.likes.all()[:10], many=True).data

    def get_is_hidden(self, obj):
        return getattr(obj, 'is_hidden_by_user', False)

    def get_is_saved(self, obj):
        return getattr(obj, 'is_saved_by_user', False)

    def get_interest_count(self, obj):
        return obj.interested_users.count()

    def get_is_interested(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.interested_users.filter(user=request.user).exists()
        return False

    def get_my_reaction(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            r = Reaction.objects.filter(user=request.user, post=obj).first()
            return r.reaction_type if r else None
        return None

    def get_reaction_summary(self, obj):
        from django.db.models import Count
        qs = obj.reactions.values('reaction_type').annotate(count=Count('id'))
        return {item['reaction_type']: item['count'] for item in qs}
