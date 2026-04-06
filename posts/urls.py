from django.urls import path
from .views import (
    PostListCreateView, PostDetailView, PostLikeView,
    CommentCreateView, CommentLikeView, CommentDeleteView,
    ReplyCreateView, ReplyLikeView, ReplyDeleteView,
    StoryListCreateView, StoryDeleteView,
    PostHideView, PostSaveView, SavedPostListView,
    EventInterestView, EventListView, ReactionView,
)

urlpatterns = [
    path('', PostListCreateView.as_view()),
    path('<int:pk>/', PostDetailView.as_view()),
    path('<int:pk>/like/', PostLikeView.as_view()),
    path('<int:pk>/react/', ReactionView.as_view()),
    path('<int:pk>/hide/', PostHideView.as_view()),
    path('<int:pk>/save/', PostSaveView.as_view()),
    path('<int:pk>/interest/', EventInterestView.as_view()),
    path('saved/', SavedPostListView.as_view()),
    path('events/', EventListView.as_view()),
    path('<int:pk>/comments/', CommentCreateView.as_view()),
    path('comments/<int:pk>/', CommentDeleteView.as_view()),
    path('comments/<int:pk>/like/', CommentLikeView.as_view()),
    path('comments/<int:pk>/replies/', ReplyCreateView.as_view()),
    path('replies/<int:pk>/', ReplyDeleteView.as_view()),
    path('replies/<int:pk>/like/', ReplyLikeView.as_view()),
    path('stories/', StoryListCreateView.as_view()),
    path('stories/<int:pk>/', StoryDeleteView.as_view()),
]
