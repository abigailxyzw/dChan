from django.contrib import admin

from posts.models import Post, ScrapeJob, Board, Platform, RedditPost, Subreddit, BBSPinkPost

admin.site.register(Post)
admin.site.register(ScrapeJob)
admin.site.register(Platform)
admin.site.register(Board)
admin.site.register(RedditPost)
admin.site.register(Subreddit)
admin.site.register(BBSPinkPost)
