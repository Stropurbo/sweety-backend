from django.contrib import admin
from .models import Post, Comment, Reply


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('author', 'visibility', 'created_at')
    list_filter = ('visibility', 'created_at')
    search_fields = ('author__email', 'content')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'created_at')
    search_fields = ('author__email', 'content')


@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ('author', 'comment', 'created_at')
    search_fields = ('author__email', 'content')
