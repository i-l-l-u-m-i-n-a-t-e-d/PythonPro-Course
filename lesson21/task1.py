from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "category"
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "tag"
        verbose_name_plural = "tags"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Post(models.Model):
  
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
    )

    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name="posts",
    )

    


# Komendy po zapisaniu zmian:

# python manage.py makemigrations blog
# python manage.py migrate
# python manage.py check
