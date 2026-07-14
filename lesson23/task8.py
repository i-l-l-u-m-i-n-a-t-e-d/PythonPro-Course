# config/urls.py
from django.contrib.auth import views as auth_views
from django.urls import path

urlpatterns = [
    path(
        'password-change/',
        auth_views.PasswordChangeView.as_view(
            template_name='users/password_change_form.html'
        ),
        name='password_change',
    ),
    path(
        'password-change/done/',
        auth_views.PasswordChangeDoneView.as_view(
            template_name='users/password_change_done.html'
        ),
        name='password_change_done',
    ),
]


# templates/users/password_change_form.html
"""
{% extends "base.html" %}

{% block content %}
<h1>Zmiana hasla</h1>
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Zmien haslo</button>
</form>
{% endblock %}
"""


# templates/users/password_change_done.html
"""
{% extends "base.html" %}

{% block content %}
<h1>Haslo zostalo zmienione</h1>
<p>Zmiana hasla zakonczyla sie poprawnie.</p>
<p><a href="{% url 'profile' %}">Wroc do profilu</a></p>
{% endblock %}
"""
