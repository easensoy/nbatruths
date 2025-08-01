from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, TemplateView
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.cache import cache
from django.db.models import Q, Count, F, Prefetch
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
from django.contrib import messages
from taggit.models import Tag
import json
from datetime import datetime, timedelta

from .models import Article, Category, NBATeam, NBAPlayer, PlayerStats, ArticleView, Newsletter
from .forms import NewsletterSignupForm


class CachedViewMixin:
    cache_timeout = 300

    def get_cache_key(self):
        return f"{self.__class__.__name__}_{self.request.path}_{self.request.GET.urlencode()}"


class HomeView(TemplateView):
    template_name = 'blog/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Featured articles
        featured_articles = Article.objects.filter(
            status='published', 
            is_featured=True
        ).select_related('author', 'category').order_by('-published_at')[:3]
        
        # Recent articles
        recent_articles = Article.objects.filter(
            status='published'
        ).select_related('author', 'category').order_by('-published_at')[:8]
        
        # Thunder specific content
        thunder_team = NBATeam.objects.filter(name__icontains='Thunder').first()
        thunder_articles = Article.objects.filter(
            status='published',
            related_teams=thunder_team
        ).select_related('author', 'category').order_by('-published_at')[:4] if thunder_team else []
        
        # Popular articles (by view count)
        popular_articles = Article.objects.filter(
            status='published'
        ).order_by('-view_count')[:5]
        
        context.update({
            'featured_articles': featured_articles,
            'recent_articles': recent_articles,
            'thunder_articles': thunder_articles,
            'popular_articles': popular_articles,
            'newsletter_form': NewsletterSignupForm(),
        })
        
        return context


class ArticleListView(ListView):
    model = Article
    template_name = 'blog/article_list.html'
    context_object_name = 'articles'
    paginate_by = 12

    def get_queryset(self):
        return Article.objects.filter(
            status='published'
        ).select_related('author', 'category').prefetch_related('tags').order_by('-published_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'All Articles'
        return context


class ArticleDetailView(DetailView):
    model = Article
    template_name = 'blog/article_detail.html'
    context_object_name = 'article'

    def get_queryset(self):
        return Article.objects.filter(
            status='published'
        ).select_related('author', 'category').prefetch_related(
            'related_players__team',
            'related_teams',
            'tags'
        )

    def get_object(self):
        article = super().get_object()
        
        # Track article view
        self.track_article_view(article)
        
        return article

    def track_article_view(self, article):
        ip_address = self.get_client_ip()
        user = self.request.user if self.request.user.is_authenticated else None
        
        # Check if this IP/user has already viewed this article today
        today = timezone.now().date()
        existing_view = ArticleView.objects.filter(
            article=article,
            ip_address=ip_address,
            timestamp__date=today
        ).exists()
        
        if not existing_view:
            ArticleView.objects.create(
                article=article,
                user=user,
                ip_address=ip_address,
                user_agent=self.request.META.get('HTTP_USER_AGENT', '')
            )
            article.increment_views()

    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        article = context['article']
        
        # Related articles
        related_articles = Article.objects.filter(
            status='published'
        ).filter(
            Q(category=article.category) |
            Q(related_teams__in=article.related_teams.all()) |
            Q(related_players__in=article.related_players.all())
        ).exclude(id=article.id).distinct()[:4]
        
        # Player stats for related players
        player_stats = {}
        for player in article.related_players.all():
            latest_stats = PlayerStats.objects.filter(player=player).first()
            if latest_stats:
                player_stats[player.id] = latest_stats
        
        context.update({
            'related_articles': related_articles,
            'player_stats': player_stats,
        })
        
        return context


class CategoryListView(ListView):
    model = Category
    template_name = 'blog/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return Category.objects.annotate(
            article_count=Count('article', filter=Q(article__status='published'))
        ).order_by('name')


class CategoryDetailView(DetailView):
    model = Category
    template_name = 'blog/category_detail.html'
    context_object_name = 'category'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = context['category']
        
        articles = Article.objects.filter(
            category=category,
            status='published'
        ).select_related('author').order_by('-published_at')
        
        paginator = Paginator(articles, 12)
        page = self.request.GET.get('page')
        
        try:
            articles = paginator.page(page)
        except PageNotAnInteger:
            articles = paginator.page(1)
        except EmptyPage:
            articles = paginator.page(paginator.num_pages)
        
        context['articles'] = articles
        return context


class ThunderView(TemplateView):
    template_name = 'blog/thunder.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get Thunder team
        thunder_team = get_object_or_404(NBATeam, name__icontains='Thunder')
        
        # Thunder articles
        thunder_articles = Article.objects.filter(
            status='published',
            related_teams=thunder_team
        ).select_related('author', 'category').order_by('-published_at')[:10]
        
        # Thunder players with latest stats
        thunder_players = NBAPlayer.objects.filter(
            team=thunder_team
        ).prefetch_related(
            Prefetch('stats', queryset=PlayerStats.objects.order_by('-season'))
        ).order_by('name')
        
        # Team stats summary
        team_stats = {}
        if thunder_players.exists():
            latest_season = PlayerStats.objects.filter(
                player__team=thunder_team
            ).values_list('season', flat=True).first()
            
            if latest_season:
                season_stats = PlayerStats.objects.filter(
                    player__team=thunder_team,
                    season=latest_season
                )
                
                team_stats = {
                    'avg_points': season_stats.aggregate(avg=models.Avg('points_per_game'))['avg'],
                    'avg_rebounds': season_stats.aggregate(avg=models.Avg('rebounds_per_game'))['avg'],
                    'avg_assists': season_stats.aggregate(avg=models.Avg('assists_per_game'))['avg'],
                }
        
        context.update({
            'thunder_team': thunder_team,
            'thunder_articles': thunder_articles,
            'thunder_players': thunder_players,
            'team_stats': team_stats,
        })
        
        return context


class PlayerListView(ListView):
    model = NBAPlayer
    template_name = 'blog/player_list.html'
    context_object_name = 'players'
    paginate_by = 20

    def get_queryset(self):
        queryset = NBAPlayer.objects.select_related('team').prefetch_related(
            Prefetch('stats', queryset=PlayerStats.objects.order_by('-season'))
        ).order_by('team__city', 'name')
        
        # Filter by team if specified
        team_filter = self.request.GET.get('team')
        if team_filter:
            queryset = queryset.filter(team__abbreviation=team_filter)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['teams'] = NBATeam.objects.all().order_by('city')
        context['selected_team'] = self.request.GET.get('team', '')
        return context


class PlayerDetailView(DetailView):
    model = NBAPlayer
    template_name = 'blog/player_detail.html'
    context_object_name = 'player'

    def get_queryset(self):
        return NBAPlayer.objects.select_related('team').prefetch_related('stats')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        player = context['player']
        
        # Player articles
        player_articles = Article.objects.filter(
            status='published',
            related_players=player
        ).select_related('author', 'category').order_by('-published_at')[:5]
        
        # Player stats history
        stats_history = PlayerStats.objects.filter(player=player).order_by('-season')
        
        context.update({
            'player_articles': player_articles,
            'stats_history': stats_history,
        })
        
        return context


class SearchView(ListView):
    model = Article
    template_name = 'blog/search_results.html'
    context_object_name = 'articles'
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return Article.objects.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(excerpt__icontains=query) |
                Q(tags__name__icontains=query)
            ).filter(status='published').distinct().select_related('author', 'category')
        return Article.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context


class TaggedArticlesView(ListView):
    model = Article
    template_name = 'blog/tagged_articles.html'
    context_object_name = 'articles'
    paginate_by = 12

    def get_queryset(self):
        tag_slug = self.kwargs['slug']
        return Article.objects.filter(
            tags__slug=tag_slug,
            status='published'
        ).select_related('author', 'category').order_by('-published_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tag_slug = self.kwargs['slug']
        context['tag'] = get_object_or_404(Tag, slug=tag_slug)
        return context


# AJAX Views
@csrf_exempt
def increment_article_views(request):
    if request.method == 'POST':
        article_id = request.POST.get('article_id')
        try:
            article = Article.objects.get(id=article_id)
            article.increment_views()
            return JsonResponse({'success': True, 'views': article.view_count})
        except Article.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Article not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@csrf_exempt
def newsletter_signup(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            newsletter, created = Newsletter.objects.get_or_create(email=email)
            if created:
                return JsonResponse({'success': True, 'message': 'Successfully subscribed!'})
            else:
                return JsonResponse({'success': False, 'message': 'Email already subscribed.'})
        return JsonResponse({'success': False, 'message': 'Invalid email address.'})
    return JsonResponse({'success': False, 'message': 'Invalid request.'})