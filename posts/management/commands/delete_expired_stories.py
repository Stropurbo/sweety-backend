from django.core.management.base import BaseCommand
from django.utils import timezone
from posts.models import Story


class Command(BaseCommand):
    help = 'Delete expired stories (older than 24 hours)'

    def handle(self, *args, **kwargs):
        deleted, _ = Story.objects.filter(expires_at__lte=timezone.now()).delete()
        self.stdout.write(f'Deleted {deleted} expired stories.')
