from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    # Homepage
    path('', views.HomeView.as_view(), name='home'),
    
    # Article URLs
    path('articles/', views.ArticleListView.as_view(), name='article_list'),
    path('article/<slug:slug>/', views.ArticleDetailView.as_view(), name='article_detail'),
    
    # Category URLs
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('category/<slug:slug>/', views.CategoryDetailView.as_view(), name='category_detail'),
    
    # NBA specific URLs
    path('thunder/', views.ThunderView.as_view(), name='thunder'),
    path('players/', views.PlayerListView.as_view(), name='player_list'),
    path('player/<int:pk>/', views.PlayerDetailView.as_view(), name='player_detail'),
    
    # Search and tags
    path('search/', views.SearchView.as_view(), name='search'),
    path('tag/<slug:slug>/', views.TaggedArticlesView.as_view(), name='tagged_articles'),
    
    # AJAX endpoints
    path('ajax/increment-views/', views.increment_article_views, name='increment_views'),
    path('ajax/newsletter-signup/', views.newsletter_signup, name='newsletter_signup'),
]