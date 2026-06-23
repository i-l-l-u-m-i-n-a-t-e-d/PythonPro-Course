from django.contrib import admin

from .models import Article, Category

admin.site.site_title = "Panel Administratora Mojej Strony"
admin.site.site_header = "Panel Administratora Mojej Strony"
admin.site.index_title = "Panel Administratora Mojej Strony"

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "category", "is_published", "pub_date")
    list_filter = ("category", "is_published", "pub_date")
    search_fields = ("title", "content")

