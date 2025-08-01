from django.contrib import admin
from django.utils.html import format_html
from django.db import models
from django.forms import Textarea
from .models import (
    Article, Category, NBATeam, NBAPlayer, PlayerStats, 
    ArticleView, Comment, Newsletter
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'article_count', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')
    
    def article_count(self, obj):
        return obj.article_set.filter(status='published').count()
    article_count.short_description = 'Published Articles'


@admin.register(NBATeam)
class NBATeamAdmin(admin.ModelAdmin):
    list_display = ('city', 'name', 'abbreviation', 'conference', 'division', 'player_count')
    list_filter = ('conference', 'division')
    search_fields = ('name', 'city', 'abbreviation')
    ordering = ('city', 'name')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'city', 'abbreviation', 'conference', 'division')
        }),
        ('Visual Identity', {
            'fields': ('logo', 'primary_color', 'secondary_color'),
            'classes': ('collapse',)
        }),
    )
    
    def player_count(self, obj):
        return obj.players.count()
    player_count.short_description = 'Players'


class PlayerStatsInline(admin.TabularInline):
    model = PlayerStats
    extra = 1
    fields = (
        'season', 'games_played', 'minutes_per_game', 
        'points_per_game', 'rebounds_per_game', 'assists_per_game',
        'field_goal_percentage', 'three_point_percentage'
    )


@admin.register(NBAPlayer)
class NBAPlayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'team', 'position', 'jersey_number', 'years_pro', 'stats_count')
    list_filter = ('team', 'position', 'years_pro')
    search_fields = ('name', 'team__name', 'team__city')
    ordering = ('name',)
    inlines = [PlayerStatsInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'team', 'position', 'jersey_number')
        }),
        ('Physical Details', {
            'fields': ('height', 'weight', 'birthdate'),
            'classes': ('collapse',)
        }),
        ('Career Information', {
            'fields': ('years_pro', 'photo'),
            'classes': ('collapse',)
        }),
    )
    
    def stats_count(self, obj):
        return obj.stats.count()
    stats_count.short_description = 'Seasons'


@admin.register(PlayerStats)
class PlayerStatsAdmin(admin.ModelAdmin):
    list_display = (
        'player', 'season', 'games_played', 'points_per_game', 
        'rebounds_per_game', 'assists_per_game', 'field_goal_percentage'
    )
    list_filter = ('season', 'player__team', 'player__position')
    search_fields = ('player__name', 'season')
    ordering = ('-season', 'player__name')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('player', 'season', 'games_played', 'minutes_per_game')
        }),
        ('Scoring & Shooting', {
            'fields': (
                'points_per_game', 'field_goal_percentage', 
                'three_point_percentage', 'free_throw_percentage'
            )
        }),
        ('Other Stats', {
            'fields': (
                'rebounds_per_game', 'assists_per_game', 'steals_per_game', 
                'blocks_per_game', 'turnovers_per_game'
            )
        }),
        ('Advanced Metrics', {
            'fields': (
                'player_efficiency_rating', 'true_shooting_percentage', 'usage_rate'
            ),
            'classes': ('collapse',)
        }),
    )


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    fields = ('author', 'content', 'is_approved', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'author', 'category', 'status', 'is_featured', 
        'published_at', 'view_count', 'comment_count'
    )
    list_filter = ('status', 'is_featured', 'category', 'created_at', 'published_at')
    search_fields = ('title', 'content', 'author__username')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'
    ordering = ('-created_at',)
    
    filter_horizontal = ('related_players', 'related_teams')
    inlines = [CommentInline]
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'slug', 'subtitle', 'content', 'excerpt')
        }),
        ('Publishing', {
            'fields': ('author', 'category', 'status', 'is_featured', 'published_at')
        }),
        ('Media', {
            'fields': ('featured_image', 'featured_image_alt'),
            'classes': ('collapse',)
        }),
        ('NBA Relationships', {
            'fields': ('related_players', 'related_teams'),
            'classes': ('collapse',)
        }),
        ('SEO & Metadata', {
            'fields': ('meta_description', 'meta_keywords', 'reading_time'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('view_count',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('view_count',)
    
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 4, 'cols': 40})},
    }
    
    def comment_count(self, obj):
        return obj.comments.filter(is_approved=True).count()
    comment_count.short_description = 'Comments'
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new article
            obj.author = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['make_published', 'make_draft', 'make_featured']
    
    def make_published(self, request, queryset):
        queryset.update(status='published')
    make_published.short_description = "Mark selected articles as published"
    
    def make_draft(self, request, queryset):
        queryset.update(status='draft')
    make_draft.short_description = "Mark selected articles as draft"
    
    def make_featured(self, request, queryset):
        queryset.update(is_featured=True)
    make_featured.short_description = "Mark selected articles as featured"


@admin.register(ArticleView)
class ArticleViewAdmin(admin.ModelAdmin):
    list_display = ('article', 'user', 'ip_address', 'timestamp')
    list_filter = ('timestamp', 'article__category')
    search_fields = ('article__title', 'user__username', 'ip_address')
    readonly_fields = ('article', 'user', 'ip_address', 'timestamp', 'user_agent')
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('article', 'author', 'created_at', 'is_approved', 'content_preview')
    list_filter = ('is_approved', 'created_at', 'article__category')
    search_fields = ('content', 'author__username', 'article__title')
    date_hierarchy = 'created_at'
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'
    
    actions = ['approve_comments', 'unapprove_comments']
    
    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)
    approve_comments.short_description = "Approve selected comments"
    
    def unapprove_comments(self, request, queryset):
        queryset.update(is_approved=False)
    unapprove_comments.short_description = "Unapprove selected comments"


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at', 'is_active')
    list_filter = ('is_active', 'subscribed_at')
    search_fields = ('email',)
    date_hierarchy = 'subscribed_at'
    readonly_fields = ('subscribed_at',)
    
    actions = ['activate_subscriptions', 'deactivate_subscriptions']
    
    def activate_subscriptions(self, request, queryset):
        queryset.update(is_active=True)
    activate_subscriptions.short_description = "Activate selected subscriptions"
    
    def deactivate_subscriptions(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_subscriptions.short_description = "Deactivate selected subscriptions"


# Customize admin site
admin.site.site_header = "NBA Truths Administration"
admin.site.site_title = "NBA Truths Admin"
admin.site.index_title = "Welcome to NBA Truths Content Management"