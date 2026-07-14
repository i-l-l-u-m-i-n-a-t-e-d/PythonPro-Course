# templates/base.html
"""
<nav>
    {% if user.is_authenticated %}
        <a href="{% url 'home' %}">Strona glowna</a>
        <a href="{% url 'profile' %}">Profil</a>
        <a href="{% url 'password_change' %}">Zmien haslo</a>
        {% if user.is_staff %}
            <a href="{% url 'staff_users' %}">Uzytkownicy</a>
        {% endif %}
        <form action="{% url 'logout' %}" method="post" class="inline-form">
            {% csrf_token %}
            <button type="submit" class="link-button">Wyloguj</button>
        </form>
        <span class="hello">Witaj, {{ user.username }}!</span>
    {% else %}
        <a href="{% url 'login' %}">Zaloguj</a>
        <a href="{% url 'register' %}">Zarejestruj</a>
    {% endif %}
</nav>
"""
