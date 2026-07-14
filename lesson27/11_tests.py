# library/tests.py
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Author, Book, Copy, Genre, Reservation


class LibraryModelTests(TestCase):
    def test_model_creation(self):
        author = Author.objects.create(full_name='Ada Lovelace')
        genre = Genre.objects.create(name='Technologia')
        book = Book.objects.create(
            title='Notatki o informatyce',
            description='Krótki opis książki w katalogu.',
            publication_date='1843-01-01',
        )
        book.authors.add(author)
        book.genres.add(genre)
        copy = Copy.objects.create(book=book, inventory_number='BIB-TEST-001')

        self.assertEqual(str(author), 'Ada Lovelace')
        self.assertEqual(str(genre), 'Technologia')
        self.assertEqual(book.available_copies_count, 1)
        self.assertEqual(copy.status, Copy.Status.AVAILABLE)


class LibraryViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='reader', password='secret12345')
        cls.author = Author.objects.create(full_name='Octavia Butler')
        cls.genre = Genre.objects.create(name='Science fiction')
        cls.book = Book.objects.create(
            title='Seed to Harvest',
            description='Zbiór literatury science fiction.',
            publication_date='2007-01-01',
        )
        cls.book.authors.add(cls.author)
        cls.book.genres.add(cls.genre)
        cls.copy = Copy.objects.create(book=cls.book, inventory_number='BIB-001')

    def test_catalogue_page_returns_200(self):
        response = self.client.get(reverse('book_list'))
        self.assertEqual(response.status_code, 200)

    def test_book_detail_page_returns_200(self):
        response = self.client.get(reverse('book_detail', args=[self.book.pk]))
        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_cannot_reserve(self):
        response = self.client.post(reverse('reserve_book', args=[self.book.pk]))
        self.copy.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])
        self.assertEqual(self.copy.status, Copy.Status.AVAILABLE)

    def test_logged_in_user_can_reserve_available_copy(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('reserve_book', args=[self.book.pk]), follow=True)
        self.copy.refresh_from_db()
        reservation = Reservation.objects.get(user=self.user, copy=self.copy)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.copy.status, Copy.Status.RESERVED)
        self.assertEqual(reservation.valid_until, timezone.localdate() + timedelta(days=14))

    def test_reserved_copy_status_changes(self):
        self.client.force_login(self.user)
        self.client.post(reverse('reserve_book', args=[self.book.pk]))
        self.copy.refresh_from_db()
        self.assertEqual(self.copy.status, Copy.Status.RESERVED)

    def test_api_schema_endpoint_returns_200(self):
        response = self.client.get(reverse('schema'))
        self.assertEqual(response.status_code, 200)

    def test_swagger_ui_endpoint_returns_200(self):
        response = self.client.get(reverse('swagger-ui'))
        self.assertEqual(response.status_code, 200)
