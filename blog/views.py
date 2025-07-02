from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import (
    ListView, DetailView, TemplateView, CreateView, 
    UpdateView, DeleteView, FormView
)
from django.views.generic.dates import YearArchiveView, MonthArchiveView, DayArchiveView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.cache import cache
from django.db.models import Q, Count, F, Prefetch
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string
from django.contrib.syndication.views import Feed
from django.urls import reverse_lazy, reverse
from django.utils.html import strip_tags
from taggit.models import Tag
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

from .models import Article, Category, NBAStatistic, Comment, ArticleLike, Newsletter, ArticleView
from .business_logic import ArticleService, ContentAnalyzer
from .forms import CommentForm, NewsletterSignupForm, ContactForm

class CachedViewMixin:
    cache_timeout = 300

    def get_cache_key(self):
        return f"{self.__class__.__name__}_{self.request.path}_{self.request.GET.urlencode()}"
    
    def get_cached_context(self):
        cache_key = self.get_cache_key()
        cached_context = cache.get(cache_key)

        if cached_context is None:
            cached_context = self.get_context_data()
            cache.set(cache_key, cached_context, self.cache_timeout)
        
        return cached_context