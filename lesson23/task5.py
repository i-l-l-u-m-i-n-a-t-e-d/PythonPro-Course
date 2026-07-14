# users/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home(request):
    return render(request, 'home.html')


# config/urls.py
from django.urls import path
from users import views as user_views

urlpatterns = [
    path('', user_views.home, name='home'),
]
