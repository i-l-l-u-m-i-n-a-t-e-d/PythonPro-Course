# users/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def profile(request):
    return render(request, 'users/profile.html')


# templates/users/profile.html
"""
{% extends "base.html" %}

{% block content %}
<h1>Profil</h1>
<p>Witaj, {{ user.username }}!</p>
<p>Email: {{ user.email }}</p>
{% endblock %}
"""
