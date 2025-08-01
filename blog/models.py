from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone
from ckeditor.fields import RichTextField
from taggit.managers import TaggableManager


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('blog:category_detail', kwargs={'slug': self.slug})


class NBATeam(models.Model):
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=5)
    conference = models.CharField(max_length=20, choices=[
        ('Eastern', 'Eastern'),
        ('Western', 'Western')
    ])
    division = models.CharField(max_length=20)
    logo = models.ImageField(upload_to='team_logos/', blank=True, null=True)
    primary_color = models.CharField(max_length=7, default="#000000")
    secondary_color = models.CharField(max_length=7, default="#FFFFFF")

    def __str__(self):
        return f"{self.city} {self.name}"

    class Meta:
        ordering = ['city', 'name']


class NBAPlayer(models.Model):
    POSITION_CHOICES = [
        ('PG', 'Point Guard'),
        ('SG', 'Shooting Guard'),
        ('SF', 'Small Forward'),
        ('PF', 'Power Forward'),
        ('C', 'Center'),
    ]

    name = models.CharField(max_length=100)
    team = models.ForeignKey(NBATeam, on_delete=models.CASCADE, related_name='players')
    position = models.CharField(max_length=2, choices=POSITION_CHOICES)
    jersey_number = models.IntegerField(null=True, blank=True)
    height = models.CharField(max_length=10, blank=True)  # e.g., "6'4""
    weight = models.IntegerField(null=True, blank=True)
    birthdate = models.DateField(null=True, blank=True)
    years_pro = models.IntegerField(default=0)
    photo = models.ImageField(upload_to='player_photos/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.team.abbreviation}"

    class Meta:
        ordering = ['name']


class PlayerStats(models.Model):
    player = models.ForeignKey(NBAPlayer, on_delete=models.CASCADE, related_name='stats')
    season = models.CharField(max_length=20)  # e.g., "2024-25"
    games_played = models.IntegerField(default=0)
    minutes_per_game = models.FloatField(default=0.0)
    points_per_game = models.FloatField(default=0.0)
    rebounds_per_game = models.FloatField(default=0.0)
    assists_per_game = models.FloatField(default=0.0)
    steals_per_game = models.FloatField(default=0.0)
    blocks_per_game = models.FloatField(default=0.0)
    field_goal_percentage = models.FloatField(default=0.0)
    three_point_percentage = models.FloatField(default=0.0)
    free_throw_percentage = models.FloatField(default=0.0)
    turnovers_per_game = models.FloatField(default=0.0)
    player_efficiency_rating = models.FloatField(default=0.0)
    true_shooting_percentage = models.FloatField(default=0.0)
    usage_rate = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.player.name} - {self.season}"

    class Meta:
        unique_together = ['player', 'season']
        ordering = ['-season']


class Article(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    subtitle = models.CharField(max_length=300, blank=True)
    content = RichTextField()
    excerpt = models.TextField(max_length=500, blank=True)
    
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='articles')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    
    featured_image = models.ImageField(upload_to='articles/', blank=True, null=True)
    featured_image_alt = models.CharField(max_length=200, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_featured = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    view_count = models.PositiveIntegerField(default=0)
    reading_time = models.PositiveIntegerField(default=5)  # in minutes
    
    # NBA specific fields
    related_players = models.ManyToManyField(NBAPlayer, blank=True, related_name='articles')
    related_teams = models.ManyToManyField(NBATeam, blank=True, related_name='articles')
    
    tags = TaggableManager(blank=True)
    
    # SEO fields
    meta_description = models.CharField(max_length=160, blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['status', 'published_at']),
            models.Index(fields=['is_featured']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        
        if not self.excerpt and self.content:
            # Create excerpt from content (remove HTML tags)
            import re
            clean_content = re.sub('<.*?>', '', self.content)
            self.excerpt = clean_content[:200] + '...' if len(clean_content) > 200 else clean_content
        
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blog:article_detail', kwargs={'slug': self.slug})

    @property
    def is_published(self):
        return self.status == 'published' and self.published_at

    def increment_views(self):
        self.view_count += 1
        self.save(update_fields=['view_count'])


class ArticleView(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        unique_together = ['article', 'ip_address', 'user']


class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_approved = models.BooleanField(default=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on {self.article.title}"


class Newsletter(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.email