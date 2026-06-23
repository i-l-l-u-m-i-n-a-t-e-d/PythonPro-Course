from django.contrib import admin, messages
from django.utils.html import format_html

from .models import Car, Dealer


class CarInline(admin.TabularInline):
    model = Car
    extra = 1
    fields = ("brand", "model", "year", "price", "is_available")
    show_change_link = True


@admin.register(Dealer)
class DealerAdmin(admin.ModelAdmin):
    list_display = ("name", "address")
    search_fields = ("name", "address")
    inlines = [CarInline]


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = (
        "thumbnail",
        "full_name",
        "brand",
        "model",
        "year",
        "price",
        "is_available",
        "dealer",
    )
    search_fields = ("brand", "model")
    list_filter = ("is_available", "year")
    ordering = ("-year",)
    readonly_fields = ("year",)
    actions = ["mark_as_unavailable"]

    def full_name(self, obj):
        return f"{obj.brand} {obj.model}"

    full_name.short_description = "Pełna nazwa"

    def thumbnail(self, obj):
        if obj.photo:
            return format_html('<img src="{}" width="150" />', obj.photo.url)
        return "Brak zdjęcia"

    thumbnail.short_description = "Zdjęcie"

    def mark_as_unavailable(self, request, queryset):
        updated = queryset.update(is_available=False)
        self.message_user(
            request,
            f"{updated} samochodów oznaczono jako niedostępne.",
            messages.SUCCESS,
        )

    mark_as_unavailable.short_description = "Oznacz jako niedostępne"
