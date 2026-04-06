from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

@require_http_methods(['GET'])
def api_root(request):
    return JsonResponse({
        'name': 'Sweety API',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'auth': '/api/auth/',
            'posts': '/api/posts/',
            'friends': '/api/friends/',
            'notifications': '/api/notifications/',
        }
    })

urlpatterns = [
    path('', api_root),
    path('api/', api_root),
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/posts/', include('posts.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/friends/', include('friends.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
