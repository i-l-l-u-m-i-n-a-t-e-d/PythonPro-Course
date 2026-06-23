from datetime import timedelta

from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Article, Category

def article_list_view(request):
    articles = Article.objects.filter(is_published=True).order_by("-pub_date")
    query = request.GET.get("q", "").strip()

    if query:
        articles = articles.filter(title__icontains=query)

    recent_limit = timezone.now() - timedelta(days=3)

    context = {
        "articles": articles,
        "query": query,
        "recent_limit": recent_limit,
    }
    return render(request, "articles/article_list.html", context)

def category_list_view(request):
    categories = Category.objects.all().order_by("name")
    return render(request, "articles/category_list.html", {"categories": categories})

def category_detail_view(request, pk):
    category = get_object_or_404(Category, pk=pk)
    return render(request, "articles/category_detail.html", {"category": category})
