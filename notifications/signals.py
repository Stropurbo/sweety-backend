from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from posts.models import Post, Comment, Reply
from .models import Notification


def make(recipient, sender, notif_type, post):
    if recipient == sender:
        return
    # avoid duplicate unread notifications of same type on same post
    Notification.objects.get_or_create(
        recipient=recipient, sender=sender,
        notif_type=notif_type, post=post, is_read=False
    )


@receiver(m2m_changed, sender=Post.likes.through)
def post_liked(sender, instance, action, pk_set, **kwargs):
    if action != 'post_add' or not pk_set:
        return
    from django.contrib.auth import get_user_model
    User = get_user_model()
    for uid in pk_set:
        liker = User.objects.filter(pk=uid).first()
        if liker:
            make(instance.author, liker, 'like_post', instance)


@receiver(post_save, sender=Comment)
def comment_created(sender, instance, created, **kwargs):
    if created:
        make(instance.post.author, instance.author, 'comment', instance.post)


@receiver(post_save, sender=Reply)
def reply_created(sender, instance, created, **kwargs):
    if created:
        make(instance.comment.author, instance.author, 'reply', instance.comment.post)
