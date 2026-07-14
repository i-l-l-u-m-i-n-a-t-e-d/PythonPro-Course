# library/management/commands/seed_db.py
import random
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from library.models import Author, Book, Copy, Genre, Reservation


class Command(BaseCommand):
    help = 'Wypełnia BiblioTech autorami, gatunkami, książkami, egzemplarzami, użytkownikiem demo i przykładowymi rezerwacjami.'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Usuwa dane biblioteki przed utworzeniem nowych.')
        parser.add_argument('--authors', type=int, default=12, help='Liczba autorów do utworzenia.')
        parser.add_argument('--books', type=int, default=24, help='Liczba książek do utworzenia.')

    def handle(self, *args, **options):
        fake = Faker('pl_PL')

        if options['clear']:
            self.stdout.write('Usuwanie istniejących danych biblioteki...')
            Reservation.objects.all().delete()
            Copy.objects.all().delete()
            Book.objects.all().delete()
            Author.objects.all().delete()
            Genre.objects.all().delete()
            User.objects.filter(username__in=['demo', 'reader']).delete()

        genre_names = [
            'Fantastyka',
            'Science fiction',
            'Historia',
            'Biografia',
            'Kryminał',
            'Poezja',
            'Technologia',
            'Podróże',
            'Klasyka',
            'Literatura młodzieżowa',
        ]
        genres = [Genre.objects.get_or_create(name=name)[0] for name in genre_names]

        authors = []
        for _ in range(options['authors']):
            author, _ = Author.objects.get_or_create(full_name=fake.unique.name())
            authors.append(author)

        books = []
        for book_index in range(1, options['books'] + 1):
            title = fake.sentence(nb_words=random.randint(3, 6)).rstrip('.')
            book = Book.objects.create(
                title=title,
                description=fake.paragraph(nb_sentences=5),
                publication_date=fake.date_between(start_date='-50y', end_date='-1y'),
            )
            book.authors.set(random.sample(authors, k=random.randint(1, min(2, len(authors)))))
            book.genres.set(random.sample(genres, k=random.randint(1, 3)))
            books.append(book)

            for copy_index in range(1, random.randint(2, 5) + 1):
                status = random.choices([Copy.Status.AVAILABLE, Copy.Status.BORROWED], weights=[4, 1], k=1)[0]
                Copy.objects.create(
                    book=book,
                    inventory_number=f'BIB-{book_index:03d}-{copy_index:02d}',
                    status=status,
                )

        demo_user, created = User.objects.get_or_create(username='demo')
        if created:
            demo_user.set_password('demo12345')
            demo_user.email = 'demo@example.com'
            demo_user.save()

        available_copies = list(Copy.objects.filter(status=Copy.Status.AVAILABLE)[:3])
        for copy in available_copies:
            copy.status = Copy.Status.RESERVED
            copy.save(update_fields=['status'])
            Reservation.objects.create(
                user=demo_user,
                copy=copy,
                valid_until=timezone.localdate() + timedelta(days=14),
                status=Reservation.Status.ACTIVE,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'Utworzono {len(authors)} autorów, {len(genres)} gatunków i {len(books)} książek.'
            )
        )
