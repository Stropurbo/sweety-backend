from django.urls import path
from .views import FriendRequestView, FriendRespondView, FriendStatusView, FriendListView, PendingRequestsView, UnfriendView

urlpatterns = [
    path('request/<int:pk>/', FriendRequestView.as_view()),
    path('respond/<int:pk>/', FriendRespondView.as_view()),
    path('unfriend/<int:pk>/', UnfriendView.as_view()),
    path('status/<int:pk>/', FriendStatusView.as_view()),
    path('list/<int:pk>/', FriendListView.as_view()),
    path('pending/', PendingRequestsView.as_view()),
]
