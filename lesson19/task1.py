from django.http import HttpResponse


def info_view(request):
    return HttpResponse("Informacje o stronie")


def rules_view(request):
    return HttpResponse("Regulamin")




from django.urls import path
from . import views

urlpatterns = [
    path("info/", views.info_view, name="info"),
    path("rules/", views.rules_view, name="rules"),
]
