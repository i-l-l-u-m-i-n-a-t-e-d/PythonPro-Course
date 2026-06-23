from django.http import HttpResponse


def user_profile_view(request, username):
    return HttpResponse(f"Witaj na profilu, {username}!")


from django.urls import path
from . import views

urlpatterns = [
    path("user/<str:username>/", views.user_profile_view, name="user-profile"),
]
