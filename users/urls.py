from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LoginView, LogoutView, MeView,
    AdminStatsView, AdminDeleteUserView, AdminToggleRoleView, AdminDeletePostView,
    UserProfileView, UpdateProfileView, ChangePasswordView, SuggestedUsersView,
    UserSearchView,
)

urlpatterns = [
    path('register/', RegisterView.as_view()),
    path('login/', LoginView.as_view()),
    path('logout/', LogoutView.as_view()),
    path('me/', MeView.as_view()),
    path('token/refresh/', TokenRefreshView.as_view()),
    path('admin/stats/', AdminStatsView.as_view()),
    path('admin/users/<int:pk>/delete/', AdminDeleteUserView.as_view()),
    path('admin/users/<int:pk>/toggle-role/', AdminToggleRoleView.as_view()),
    path('admin/posts/<int:pk>/delete/', AdminDeletePostView.as_view()),
    path('profile/<int:pk>/', UserProfileView.as_view()),
    path('profile/update/', UpdateProfileView.as_view()),
    path('change-password/', ChangePasswordView.as_view()),
    path('suggested/', SuggestedUsersView.as_view()),
    path('search/', UserSearchView.as_view()),
]
