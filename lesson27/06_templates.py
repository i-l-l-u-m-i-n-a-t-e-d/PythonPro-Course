# templates/base.html
"""
<nav class="nav">
    <a class="brand" href="{% url 'home' %}">BiblioTech</a>
    <div class="nav-links">
        <a href="{% url 'book_list' %}">Katalog</a>
        <a href="{% url 'swagger-ui' %}">Swagger UI</a>
        <a href="{% url 'redoc' %}">ReDoc</a>
        {% if user.is_authenticated %}
            <a href="{% url 'my_reservations' %}">Moje rezerwacje</a>
            <form class="inline-form" method="post" action="{% url 'logout' %}">
                {% csrf_token %}
                <button type="submit" class="link-button">Wyloguj się</button>
            </form>
        {% else %}
            <a href="{% url 'login' %}">Zaloguj się</a>
            <a class="button button-small" href="{% url 'register' %}">Zarejestruj się</a>
        {% endif %}
    </div>
</nav>
"""

# templates/library/book_list.html
"""
<form class="filter-panel" method="get">
    <label>
        Wyszukiwanie
        <input type="search" name="q" value="{{ search_query }}" placeholder="Tytuł, opis, autor lub gatunek">
    </label>
    <label>
        Autor
        <select name="author">
            <option value="">Wszyscy autorzy</option>
            {% for author in authors %}
                <option value="{{ author.id }}" {% if selected_author == author.id|stringformat:"s" %}selected{% endif %}>
                    {{ author.full_name }}
                </option>
            {% endfor %}
        </select>
    </label>
    <label>
        Gatunek
        <select name="genre">
            <option value="">Wszystkie gatunki</option>
            {% for genre in genres %}
                <option value="{{ genre.id }}" {% if selected_genre == genre.id|stringformat:"s" %}selected{% endif %}>
                    {{ genre.name }}
                </option>
            {% endfor %}
        </select>
    </label>
    <button type="submit">Zastosuj</button>
    <a class="button button-muted" href="{% url 'book_list' %}">Wyczyść</a>
</form>
"""

# templates/library/book_detail.html
"""
<div class="reservation-box">
    <strong>{{ book.available_copies_count }}</strong>
    <span>dostępnych egzemplarzy</span>
    {% if book.available_copies_count > 0 %}
        {% if user.is_authenticated %}
            <form method="post" action="{% url 'reserve_book' book.pk %}">
                {% csrf_token %}
                <button type="submit">Zarezerwuj na 14 dni</button>
            </form>
        {% else %}
            <a class="button" href="{% url 'login' %}?next={% url 'book_detail' book.pk %}">Zaloguj się, aby zarezerwować</a>
        {% endif %}
    {% else %}
        <p class="small">Wszystkie egzemplarze są obecnie niedostępne.</p>
    {% endif %}
</div>
"""

# templates/library/reservations.html
"""
<h1>Moje rezerwacje</h1>

<h2>Aktualne rezerwacje</h2>
{% if current_reservations %}
    <table class="data-table">
        <thead>
            <tr>
                <th>Książka</th>
                <th>Egzemplarz</th>
                <th>Data rezerwacji</th>
                <th>Ważna do</th>
            </tr>
        </thead>
        <tbody>
            {% for reservation in current_reservations %}
                <tr>
                    <td><a href="{% url 'book_detail' reservation.copy.book.pk %}">{{ reservation.copy.book.title }}</a></td>
                    <td>{{ reservation.copy.inventory_number }}</td>
                    <td>{{ reservation.reservation_date }}</td>
                    <td>{{ reservation.valid_until }}</td>
                </tr>
            {% endfor %}
        </tbody>
    </table>
{% else %}
    <p class="empty">Nie masz aktywnych rezerwacji.</p>
{% endif %}

<h2>Historia rezerwacji</h2>
{% if historical_reservations %}
    <table class="data-table">
        <thead>
            <tr>
                <th>Książka</th>
                <th>Egzemplarz</th>
                <th>Data rezerwacji</th>
                <th>Ważna do</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            {% for reservation in historical_reservations %}
                <tr>
                    <td>{{ reservation.copy.book.title }}</td>
                    <td>{{ reservation.copy.inventory_number }}</td>
                    <td>{{ reservation.reservation_date }}</td>
                    <td>{{ reservation.valid_until }}</td>
                    <td>{{ reservation.get_status_display }}</td>
                </tr>
            {% endfor %}
        </tbody>
    </table>
{% else %}
    <p class="empty">Brak historycznych rezerwacji.</p>
{% endif %}
"""

# templates/registration/login.html
"""
<section class="auth-panel">
    <p class="eyebrow">Witaj ponownie</p>
    <h1>Logowanie</h1>
    <form method="post">
        {% csrf_token %}
        {{ form.as_p }}
        <button type="submit">Zaloguj się</button>
    </form>
</section>
"""
