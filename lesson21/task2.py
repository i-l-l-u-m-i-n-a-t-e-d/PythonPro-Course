from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Category, Post


def home(request):
    query = request.GET.get("q", "").strip()

    posts = Post.objects.all().order_by("-publication_date")

    if query:
        posts = posts.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query)
        )

    posts = posts[:5]

    context = {
        "posts": posts,
        "query": query,
    }

    return render(request, "blog/home.html", context)


def category_posts(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    posts = Post.objects.filter(category=category).order_by("-publication_date")

    context = {
        "category": category,
        "posts": posts,
    }

    return render(request, "blog/category_posts.html", context)


# -------------------------------------------------------------------------
#  blog/urls.py
# -------------------------------------------------------------------------
#
# from django.urls import path
# from . import views
#
# urlpatterns = [
#     path("", views.home, name="home"),
#     path("category/<int:category_id>/", views.category_posts, name="category_posts"),
# ]


# -------------------------------------------------------------------------
# config/urls.py
# -------------------------------------------------------------------------
#
# from django.contrib import admin
# from django.urls import include, path
#
# urlpatterns = [
#     path("admin/", admin.site.urls),
#     path("", include("blog.urls")),
# ]


# -------------------------------------------------------------------------
#  blog/templates/blog/home.html
# -------------------------------------------------------------------------
#
# <!doctype html>
# <html lang="pl">
# <head>
#     <meta charset="utf-8">
#     <title>Blog</title>
# </head>
# <body>
#     <h1>Ostatnie posty</h1>
#
#     <form method="get">
#         <input type="text" name="q" value="{{ query }}" placeholder="Szukaj w postach">
#         <button type="submit">Szukaj</button>
#     </form>
#
#     {% if query %}
#         <p>Wyniki wyszukiwania dla: <strong>{{ query }}</strong></p>
#     {% endif %}
#
#     {% for post in posts %}
#         <article>
#             <h2>{{ post.title }}</h2>
#             <p>{{ post.content|truncatewords:30 }}</p>
#             {% if post.category %}
#                 <p>Kategoria:
#                     <a href="{% url 'category_posts' post.category.id %}">
#                         {{ post.category.name }}
#                     </a>
#                 </p>
#             {% endif %}
#         </article>
#     {% empty %}
#         <p>Brak postów do wyświetlenia.</p>
#     {% endfor %}
# </body>
# </html>


# -------------------------------------------------------------------------
# blog/templates/blog/category_posts.html
# -------------------------------------------------------------------------
#
# <!doctype html>
# <html lang="pl">
# <head>
#     <meta charset="utf-8">
#     <title>Kategoria: {{ category.name }}</title>
# </head>
# <body>
#     <h1>Kategoria: {{ category.name }}</h1>
#
#     {% for post in posts %}
#         <article>
#             <h2>{{ post.title }}</h2>
#             <p>{{ post.content|truncatewords:30 }}</p>
#         </article>
#     {% empty %}
#         <p>Brak postów w tej kategorii.</p>
#     {% endfor %}
#
#     <p><a href="{% url 'home' %}">Powrót na stronę główną</a></p>
# </body>
# </html>
