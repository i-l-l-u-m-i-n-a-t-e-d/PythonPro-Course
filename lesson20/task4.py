from django.urls import path

from .views import article_list_view, category_detail_view, category_list_view

urlpatterns = [
    path("", article_list_view, name="article-list"),
    path("articles/", article_list_view, name="article-list"),
    path("categories/", category_list_view, name="category-list"),
    path("categories/<int:pk>/", category_detail_view, name="category-detail"),
]

