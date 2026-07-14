# library/models.py
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class Author(models.Model):
    full_name = models.CharField(max_length=160)
    photo = models.ImageField(upload_to='authors/', blank=True, null=True)

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return self.full_name


class Genre(models.Model):
    name = models.CharField(max_length=80, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=220)
    description = models.TextField()
    publication_date = models.DateField()
    cover = models.ImageField(upload_to='covers/', blank=True, null=True)
    authors = models.ManyToManyField(Author, related_name='books')
    genres = models.ManyToManyField(Genre, related_name='books')

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title

    @property
    def available_copies_count(self):
        return self.copies.filter(status=Copy.Status.AVAILABLE).count()


class Copy(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Dostępny'
        RESERVED = 'reserved', 'Zarezerwowany'
        BORROWED = 'borrowed', 'Wypożyczony'

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='copies')
    inventory_number = models.CharField(max_length=40, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)

    class Meta:
        ordering = ['book__title', 'inventory_number']
        verbose_name_plural = 'egzemplarze'

    def __str__(self):
        return f'{self.book.title} ({self.inventory_number})'


class Reservation(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Aktywna'
        EXPIRED = 'expired', 'Wygasła'
        CANCELLED = 'cancelled', 'Anulowana'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reservations')
    copy = models.ForeignKey(Copy, on_delete=models.CASCADE, related_name='reservations')
    reservation_date = models.DateField(auto_now_add=True)
    valid_until = models.DateField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ['-reservation_date', '-id']

    def save(self, *args, **kwargs):
        if not self.valid_until:
            self.valid_until = timezone.localdate() + timedelta(days=14)
        super().save(*args, **kwargs)

    @property
    def is_current(self):
        return self.status == self.Status.ACTIVE and self.valid_until >= timezone.localdate()

    def __str__(self):
        return f'{self.user} - {self.copy}'
