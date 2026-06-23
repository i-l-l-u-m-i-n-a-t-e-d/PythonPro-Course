from django import forms

from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "description", "price", "category"]



from django.shortcuts import redirect, render

from .forms import ProductForm


def product_create_view(request):
    if request.method == "POST":
        form = ProductForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("product-list")
    else:
        form = ProductForm()

    return render(request, "products/product_form.html", {"form": form})



from django.urls import path
from . import views

urlpatterns = [
    path("products/add/", views.product_create_view, name="product-create"),
]


# sciezka: templates/products/product_form.html


"""
{% extends "base.html" %}

{% block title %}Dodaj produkt{% endblock %}

{% block content %}
    <h2>Dodaj produkt</h2>

    <form method="post">
        {% csrf_token %}
        {{ form.as_p }}
        <button type="submit">Zapisz produkt</button>
    </form>
{% endblock %}
"""
