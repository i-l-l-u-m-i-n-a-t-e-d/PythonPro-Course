# library/admin.py
from django.contrib import admin

from .models import Author, Book, Copy, Genre, Reservation


class CopyInline(admin.TabularInline):
    model = Copy
    extra = 1
    fields = ('inventory_number', 'status')


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'book_count')
    search_fields = ('full_name',)

    @admin.display(description='Książki')
    def book_count(self, obj):
        return obj.books.count()


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name', 'book_count')
    search_fields = ('name',)

    @admin.display(description='Książki')
    def book_count(self, obj):
        return obj.books.count()


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'publication_date', 'author_names', 'copy_count', 'available_count')
    list_filter = ('genres', 'publication_date')
    search_fields = ('title', 'description', 'authors__full_name', 'genres__name')
    filter_horizontal = ('authors', 'genres')
    inlines = [CopyInline]

    @admin.display(description='Autorzy')
    def author_names(self, obj):
        return ', '.join(author.full_name for author in obj.authors.all())

    @admin.display(description='Egzemplarze')
    def copy_count(self, obj):
        return obj.copies.count()

    @admin.display(description='Dostępne')
    def available_count(self, obj):
        return obj.copies.filter(status=Copy.Status.AVAILABLE).count()


@admin.register(Copy)
class CopyAdmin(admin.ModelAdmin):
    list_display = ('inventory_number', 'book', 'status')
    list_filter = ('status', 'book__genres')
    search_fields = ('inventory_number', 'book__title')
    autocomplete_fields = ('book',)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('user', 'copy', 'book_title', 'reservation_date', 'valid_until', 'status')
    list_filter = ('status', 'reservation_date', 'valid_until')
    search_fields = ('user__username', 'copy__inventory_number', 'copy__book__title')
    readonly_fields = ('reservation_date',)
    autocomplete_fields = ('user', 'copy')

    @admin.display(description='Książka')
    def book_title(self, obj):
        return obj.copy.book.title
