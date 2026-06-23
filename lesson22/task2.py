from django.db import models


class Dealer(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()

    def __str__(self):
        return self.name


class Car(models.Model):
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    photo = models.ImageField(upload_to="cars/", blank=True, null=True)
    owner_website = models.URLField(blank=True)
    is_available = models.BooleanField(default=True)
    dealer = models.ForeignKey(
        Dealer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cars",
    )

    def __str__(self):
        return f"{self.brand} {self.model} ({self.year})"
