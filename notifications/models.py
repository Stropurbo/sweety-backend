from django.db import models
from django.conf import settings


class Notification(models.Model):
    TYPE_CHOICES = [
        ('like_post',     'Liked your post'),
        ('like_comment',  'Liked your comment'),
        ('like_reply',    'Liked your reply'),
        ('comment',       'Commented on your post'),
        ('reply',         'Replied to your comment'),
        ('friend_request','Sent you a friend request'),
        ('friend_accept', 'Accepted your friend request'),
        ('event_interest','Is interested in your event'),
    ]
    recipient  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    sender     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_notifications')
    notif_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    post       = models.ForeignKey('posts.Post', on_delete=models.CASCADE, null=True, blank=True)
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
