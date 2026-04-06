from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.pagination import CursorPagination
from django.shortcuts import get_object_or_404
from django.db.models import Exists, OuterRef
import cloudinary.uploader
from .models import Post, PostMedia, Comment, Reply, Story, HiddenPost, SavedPost, EventInterest, Reaction
from .serializers import PostSerializer, CommentSerializer, ReplySerializer, StorySerializer


class PostCursorPagination(CursorPagination):
    page_size = 20
    ordering = '-created_at'
    cursor_query_param = 'cursor'


def annotate_posts(queryset, user):
    """Annotate is_liked, is_hidden, is_saved in a single query pass."""
    return queryset.annotate(
        is_liked_by_user=Exists(
            Post.likes.through.objects.filter(post_id=OuterRef('pk'), user_id=user.id)
        ),
        is_hidden_by_user=Exists(
            HiddenPost.objects.filter(post_id=OuterRef('pk'), user_id=user.id)
        ),
        is_saved_by_user=Exists(
            SavedPost.objects.filter(post_id=OuterRef('pk'), user_id=user.id)
        ),
    ).select_related('author').prefetch_related(
        'media',
        'reactions',
        'comments__author',
        'comments__replies__author',
        'comments__likes',
    )


def upload_media(files, resource_type='image'):
    urls = []
    for f in files:
        upload = cloudinary.uploader.upload(f, resource_type=resource_type, folder='sweety/posts')
        urls.append(upload.get('secure_url'))
    return urls


class PostListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        hidden_ids = HiddenPost.objects.filter(user=request.user).values_list('post_id', flat=True)
        posts = (Post.objects.filter(visibility='public') | Post.objects.filter(author=request.user))
        posts = posts.distinct().exclude(id__in=hidden_ids).order_by('-created_at')
        posts = annotate_posts(posts, request.user)
        paginator = PostCursorPagination()
        page = paginator.paginate_queryset(posts, request)
        serializer = PostSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        data = request.data.copy()
        serializer = PostSerializer(data=data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        post = serializer.save(
            author=request.user,
            post_type=request.data.get('post_type', 'post'),
            event_title=request.data.get('event_title', ''),
            event_date=request.data.get('event_date') or None,
            event_location=request.data.get('event_location', ''),
            article_title=request.data.get('article_title', ''),
        )

        order = 0
        for f in request.FILES.getlist('images'):
            url = cloudinary.uploader.upload(f, folder='sweety/posts').get('secure_url')
            PostMedia.objects.create(post=post, url=url, media_type='image', order=order)
            order += 1
        for f in request.FILES.getlist('videos'):
            url = cloudinary.uploader.upload(f, resource_type='video', folder='sweety/posts').get('secure_url')
            PostMedia.objects.create(post=post, url=url, media_type='video', order=order)
            order += 1

        # backward compat single fields
        if 'image' in request.FILES and not request.FILES.getlist('images'):
            url = cloudinary.uploader.upload(request.FILES['image'], folder='sweety/posts').get('secure_url')
            post.image = url
            post.save()
            PostMedia.objects.create(post=post, url=url, media_type='image', order=0)
        if 'video' in request.FILES and not request.FILES.getlist('videos'):
            url = cloudinary.uploader.upload(request.FILES['video'], resource_type='video', folder='sweety/posts').get('secure_url')
            post.video = url
            post.save()
            PostMedia.objects.create(post=post, url=url, media_type='video', order=1)

        return Response(PostSerializer(post, context={'request': request}).data, status=status.HTTP_201_CREATED)


class PostDetailView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, pk, user):
        post = get_object_or_404(Post, pk=pk)
        if post.visibility == 'private' and post.author != user and not user.is_staff:
            return None
        return post

    def get(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        if post.visibility == 'private' and post.author != request.user and not request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        post = annotate_posts(Post.objects.filter(pk=pk), request.user).first()
        return Response(PostSerializer(post, context={'request': request}).data)

    def patch(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        if post.author != request.user and not request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)

        save_kwargs = {}

        # remove specific media by id
        remove_ids = request.data.getlist('remove_media_ids')
        if remove_ids:
            PostMedia.objects.filter(post=post, id__in=remove_ids).delete()

        # add new images
        order = post.media.count()
        for f in request.FILES.getlist('images'):
            url = cloudinary.uploader.upload(f, folder='sweety/posts').get('secure_url')
            PostMedia.objects.create(post=post, url=url, media_type='image', order=order)
            order += 1
        for f in request.FILES.getlist('videos'):
            url = cloudinary.uploader.upload(f, resource_type='video', folder='sweety/posts').get('secure_url')
            PostMedia.objects.create(post=post, url=url, media_type='video', order=order)
            order += 1

        # backward compat
        if 'image' in request.FILES:
            url = cloudinary.uploader.upload(request.FILES['image'], folder='sweety/posts').get('secure_url')
            save_kwargs['image'] = url
            PostMedia.objects.create(post=post, url=url, media_type='image', order=order)
        elif request.data.get('remove_image') == 'true':
            save_kwargs['image'] = ''
        if 'video' in request.FILES:
            url = cloudinary.uploader.upload(request.FILES['video'], resource_type='video', folder='sweety/posts').get('secure_url')
            save_kwargs['video'] = url
            PostMedia.objects.create(post=post, url=url, media_type='video', order=order)
        elif request.data.get('remove_video') == 'true':
            save_kwargs['video'] = ''

        allowed = {k: v for k, v in request.data.items() if k in ('content', 'visibility')}
        serializer = PostSerializer(post, data=allowed, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save(**save_kwargs)
            return Response(PostSerializer(post, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        if post.author != request.user and not request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CommentDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        if comment.author != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        comment.content = request.data.get('content', comment.content)
        comment.save()
        return Response(CommentSerializer(comment, context={'request': request}).data)

    def delete(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        if comment.author != request.user and not request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReplyDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        reply = get_object_or_404(Reply, pk=pk)
        if reply.author != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        reply.content = request.data.get('content', reply.content)
        reply.save()
        return Response(ReplySerializer(reply, context={'request': request}).data)

    def delete(self, request, pk):
        reply = get_object_or_404(Reply, pk=pk)
        if reply.author != request.user and not request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        reply.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PostLikeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        if post.visibility == 'private' and post.author != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if post.likes.filter(id=request.user.id).exists():
            post.likes.remove(request.user)
            liked = False
        else:
            post.likes.add(request.user)
            liked = True
        count = post.likes.count()
        Post.objects.filter(pk=pk).update(likes_count=count)
        return Response({'liked': liked, 'likes_count': count})


class CommentCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        page = int(request.query_params.get('page', 1))
        page_size = 10
        offset = (page - 1) * page_size
        comments = Comment.objects.filter(post=post).select_related('author').prefetch_related(
            'replies__author', 'likes'
        ).order_by('created_at')[offset:offset + page_size]
        total = Comment.objects.filter(post=post).count()
        return Response({
            'results': CommentSerializer(comments, many=True, context={'request': request}).data,
            'total': total,
            'has_more': (offset + page_size) < total,
        })

    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        if post.visibility == 'private' and post.author != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = CommentSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(author=request.user, post=post)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentLikeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        if comment.likes.filter(id=request.user.id).exists():
            comment.likes.remove(request.user)
            liked = False
        else:
            comment.likes.add(request.user)
            liked = True
        return Response({'liked': liked, 'likes_count': comment.likes.count()})


class ReplyCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        serializer = ReplySerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(author=request.user, comment=comment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReplyLikeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        reply = get_object_or_404(Reply, pk=pk)
        if reply.likes.filter(id=request.user.id).exists():
            reply.likes.remove(request.user)
            liked = False
        else:
            reply.likes.add(request.user)
            liked = True
        return Response({'liked': liked, 'likes_count': reply.likes.count()})


class PostHideView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        _, created = HiddenPost.objects.get_or_create(user=request.user, post=post)
        return Response({'hidden': True})

    def delete(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        HiddenPost.objects.filter(user=request.user, post=post).delete()
        return Response({'hidden': False})


class PostSaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        _, created = SavedPost.objects.get_or_create(user=request.user, post=post)
        return Response({'saved': True})

    def delete(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        SavedPost.objects.filter(user=request.user, post=post).delete()
        return Response({'saved': False})


class SavedPostListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        saved_ids = SavedPost.objects.filter(user=request.user).values_list('post_id', flat=True)
        posts = annotate_posts(Post.objects.filter(id__in=saved_ids), request.user)
        paginator = PostCursorPagination()
        page = paginator.paginate_queryset(posts, request)
        return paginator.get_paginated_response(PostSerializer(page, many=True, context={'request': request}).data)


class StoryListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        from django.utils import timezone
        stories = Story.objects.filter(expires_at__gt=timezone.now()).select_related('author')
        # group by author — latest story per author first
        return Response(StorySerializer(stories, many=True).data)

    def post(self, request):
        image_url = None
        if 'image' in request.FILES:
            res = cloudinary.uploader.upload(request.FILES['image'], folder='sweety/stories')
            image_url = res.get('secure_url')
        text = request.data.get('text', '')
        bg_color = request.data.get('bg_color', '#1890ff')
        if not image_url and not text.strip():
            return Response({'error': 'Story must have image or text.'}, status=400)
        story = Story.objects.create(author=request.user, image=image_url, text=text, bg_color=bg_color)
        return Response(StorySerializer(story).data, status=201)


class StoryDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        story = get_object_or_404(Story, pk=pk)
        if story.author != request.user and not request.user.is_staff:
            return Response(status=403)
        story.delete()
        return Response(status=204)


class EventInterestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk, post_type='event')
        if post.author == request.user:
            return Response({'error': 'Cannot mark interest in your own event.'}, status=400)
        _, created = EventInterest.objects.get_or_create(user=request.user, post=post)
        if created:
            from notifications.models import Notification
            Notification.objects.get_or_create(
                recipient=post.author, sender=request.user,
                notif_type='event_interest', post=post, is_read=False
            )
        return Response({'interested': True, 'interest_count': post.interested_users.count()})

    def delete(self, request, pk):
        post = get_object_or_404(Post, pk=pk, post_type='event')
        EventInterest.objects.filter(user=request.user, post=post).delete()
        return Response({'interested': False, 'interest_count': post.interested_users.count()})


class ReactionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        reaction_type = request.data.get('reaction_type', 'like')
        existing = Reaction.objects.filter(user=request.user, post=post).first()
        if existing:
            if existing.reaction_type == reaction_type:
                existing.delete()
                count = post.reactions.count()
                Post.objects.filter(pk=pk).update(likes_count=count)
                return Response({'reacted': False, 'reaction_type': None, 'likes_count': count})
            else:
                old_type = existing.reaction_type
                existing.reaction_type = reaction_type
                existing.save()
                count = post.reactions.count()
                return Response({'reacted': True, 'reaction_type': reaction_type, 'old_type': old_type, 'likes_count': count})
        Reaction.objects.create(user=request.user, post=post, reaction_type=reaction_type)
        count = post.reactions.count()
        Post.objects.filter(pk=pk).update(likes_count=count)
        return Response({'reacted': True, 'reaction_type': reaction_type, 'old_type': None, 'likes_count': count})


class EventListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Q
        from friends.models import Friendship
        from django.utils import timezone

        friend_ids = Friendship.objects.filter(
            status='accepted'
        ).filter(
            Q(sender=request.user) | Q(receiver=request.user)
        ).values_list('sender_id', 'receiver_id')

        friend_set = set()
        for s, r in friend_ids:
            friend_set.add(s)
            friend_set.add(r)
        friend_set.discard(request.user.id)

        # own events + friends' events, upcoming only
        events = Post.objects.filter(
            post_type='event',
            visibility='public',
        ).filter(
            Q(author=request.user) | Q(author_id__in=friend_set)
        ).order_by('event_date')

        return Response(PostSerializer(events, many=True, context={'request': request}).data)
