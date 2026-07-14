# users/views.py
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.shortcuts import render


@staff_member_required(login_url='login')
def staff_users(request):
    users = User.objects.all().order_by('username')
    return render(request, 'users/staff_users.html', {'users': users})


# templates/users/staff_users.html
"""
{% extends "base.html" %}

{% block content %}
<h1>Lista uzytkownikow</h1>
<table>
    <thead>
        <tr>
            <th>Nazwa</th>
            <th>Email</th>
            <th>Staff</th>
        </tr>
    </thead>
    <tbody>
        {% for person in users %}
            <tr>
                <td>{{ person.username }}</td>
                <td>{{ person.email }}</td>
                <td>{{ person.is_staff }}</td>
            </tr>
        {% empty %}
            <tr>
                <td colspan="3">Brak uzytkownikow.</td>
            </tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
"""


# config/urls.py
from django.urls import path
from users import views as user_views

urlpatterns = [
    path('staff-users/', user_views.staff_users, name='staff_users'),
]
