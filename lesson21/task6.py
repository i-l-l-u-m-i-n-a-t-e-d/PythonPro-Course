
INSTALLED_APPS = [
    # Django:
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Wymagane przez django-allauth:
    "django.contrib.sites",

    # Aplikacje projektu:
    "blog",

    # django-allauth:
    "allauth",
    "allauth.account",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",

    # Wymagane przez nowsze wersje django-allauth:
    "allauth.account.middleware.AccountMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

LOGIN_REDIRECT_URL = "/"
ACCOUNT_LOGOUT_REDIRECT_URL = "/"

ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]


# -------------------------------------------------------------------------
# config/urls.py
# -------------------------------------------------------------------------
#
# from django.contrib import admin
# from django.urls import include, path
#
# urlpatterns = [
#     path("admin/", admin.site.urls),
#     path("", include("blog.urls")),
#     path("accounts/", include("allauth.urls")),
# ]


# Komendy po zapisaniu zmian:
# python manage.py migrate
# python manage.py check
# python manage.py runserver
