from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Friendship
from users.models import User
from users.serializers import UserSerializer
from notifications.models import Notification


class FriendRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        receiver = get_object_or_404(User, pk=pk)
        if receiver == request.user:
            return Response({'error': 'Cannot send request to yourself'}, status=400)

        # check reverse request exists
        reverse = Friendship.objects.filter(sender=receiver, receiver=request.user).first()
        if reverse:
            if reverse.status == 'pending':
                reverse.status = 'accepted'
                reverse.save()
                return Response({'status': 'accepted'})
            return Response({'status': 'already_friends'})

        obj, created = Friendship.objects.get_or_create(sender=request.user, receiver=receiver)
        if not created:
            return Response({'status': obj.status})

        # notification
        Notification.objects.get_or_create(
            recipient=receiver, sender=request.user,
            notif_type='friend_request', post=None, is_read=False
        )
        return Response({'status': 'pending'})


class FriendRespondView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        sender = get_object_or_404(User, pk=pk)
        action = request.data.get('action')  # 'accept' | 'reject'
        fr = get_object_or_404(Friendship, sender=sender, receiver=request.user)
        if action == 'accept':
            fr.status = 'accepted'
            fr.save()
            Notification.objects.get_or_create(
                recipient=sender, sender=request.user,
                notif_type='friend_accept', post=None, is_read=False
            )
            return Response({'status': 'accepted'})
        fr.delete()
        return Response({'status': 'rejected'})


class FriendStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        other = get_object_or_404(User, pk=pk)
        fr = Friendship.objects.filter(
            Q(sender=request.user, receiver=other) | Q(sender=other, receiver=request.user)
        ).first()
        if not fr:
            return Response({'status': 'none'})
        if fr.status == 'accepted':
            return Response({'status': 'friends'})
        if fr.sender == request.user:
            return Response({'status': 'pending_sent'})
        return Response({'status': 'pending_received', 'from_id': other.id})


class UnfriendView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        other = get_object_or_404(User, pk=pk)
        Friendship.objects.filter(
            Q(sender=request.user, receiver=other) | Q(sender=other, receiver=request.user)
        ).delete()
        return Response({'status': 'unfriended'})


class FriendListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        friendships = Friendship.objects.filter(
            Q(sender=user) | Q(receiver=user), status='accepted'
        ).select_related('sender', 'receiver')
        friends = []
        for f in friendships:
            friend = f.receiver if f.sender == user else f.sender
            friends.append(friend)
        return Response(UserSerializer(friends, many=True).data)


class PendingRequestsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pending = Friendship.objects.filter(receiver=request.user, status='pending').select_related('sender')
        data = [{'id': f.id, 'sender': UserSerializer(f.sender).data} for f in pending]
        return Response(data)
