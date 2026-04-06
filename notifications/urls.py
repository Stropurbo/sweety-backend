from django.urls import path
from .views import NotificationListView, NotificationMarkReadView

urlpatterns = [
    path('', NotificationListView.as_view()),
    path('read/', NotificationMarkReadView.as_view()),
    path('read/<int:pk>/', NotificationMarkReadView.as_view()),
]
