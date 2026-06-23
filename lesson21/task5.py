import random

from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from blog.models import Author, Category, Post, Tag


class Command(BaseCommand):
    help = "Seeds the blog database with categories, tags and sample posts."

    def handle(self, *args, **kwargs):
        fake = Faker("pl_PL")

        self.stdout.write("Deleting old posts, categories and tags...")
        Post.objects.all().delete()
        Category.objects.all().delete()
        Tag.objects.all().delete()

        category_names = [
            "Technologia",
            "Podróże",
            "Kulinaria",
            "Sport",
            "Kultura",
            "Nauka",
            "Zdrowie",
            "Biznes",
        ]

        tag_names = [
            "django",
            "python",
            "webdev",
            "poradnik",
            "inspiracje",
            "praktyka",
            "testy",
            "baza-danych",
            "orm",
            "projekt",
        ]

        categories = []
        for name in category_names:
            category = Category.objects.create(name=name)
            categories.append(category)

        tags = []
        for name in tag_names:
            tag = Tag.objects.create(name=name)
            tags.append(tag)

        authors = list(Author.objects.all())

        if not authors:
            self.stdout.write("No authors found. Creating 10 test authors...")
            for _ in range(10):
                author = Author.objects.create(
                    name=fake.name(),
                    email=fake.unique.email(),
                )
                authors.append(author)

        posts = []

        for _ in range(100):
            post = Post.objects.create(
                title=fake.sentence(nb_words=6),
                content="\n\n".join(fake.paragraphs(nb=5)),
                author=random.choice(authors),
                category=random.choice(categories),
                publication_date=fake.date_time_this_year(
                    before_now=True,
                    after_now=False,
                    tzinfo=timezone.get_current_timezone(),
                ),
            )

            selected_tags = random.sample(tags, random.randint(1, 5))
            post.tags.set(selected_tags)

            posts.append(post)

        self.stdout.write(self.style.SUCCESS(f"Created categories: {len(categories)}"))
        self.stdout.write(self.style.SUCCESS(f"Created tags: {len(tags)}"))
        self.stdout.write(self.style.SUCCESS(f"Created posts: {len(posts)}"))
        self.stdout.write(self.style.SUCCESS("Blog seeding complete."))


# Komendy:
# python manage.py seed_blog

