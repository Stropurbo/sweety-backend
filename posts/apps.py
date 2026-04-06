from django.apps import AppConfig


class PostsConfig(AppConfig):
    name = 'posts'

    def ready(self):
        import threading

        def cleanup_loop():
            import time
            while True:
                time.sleep(3600)  # wait 1 hour
                try:
                    from django.utils import timezone
                    from posts.models import Story
                    deleted, _ = Story.objects.filter(expires_at__lte=timezone.now()).delete()
                    if deleted:
                        print(f'[Story Cleanup] Deleted {deleted} expired stories.')
                except Exception as e:
                    print(f'[Story Cleanup] Error: {e}')

        t = threading.Thread(target=cleanup_loop, daemon=True)
        t.start()
