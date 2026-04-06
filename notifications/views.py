from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Notification
from users.serializers import UserSerializer


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifs = Notification.objects.filter(recipient=request.user).select_related('sender', 'post')[:40]
        data = []
        for n in notifs:
            data.append({
                'id': n.id,
                'type': n.notif_type,
                'sender': {
                    'id': n.sender.id,
                    'name': f"{n.sender.first_name} {n.sender.last_name}",
                    'avatar': n.sender.avatar,
                    'initials': f"{n.sender.first_name[0]}{n.sender.last_name[0]}".upper(),
                },
                'post_id': n.post_id,
                'post_author_id': n.post.author_id if n.post else None,
                'is_read': n.is_read,
                'created_at': n.created_at,
            })
        unread = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({'notifications': data, 'unread_count': unread})


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        qs = Notification.objects.filter(recipient=request.user, is_read=False)
        if pk:
            qs = qs.filter(pk=pk)
        qs.update(is_read=True)
        return Response({'status': 'ok'})
