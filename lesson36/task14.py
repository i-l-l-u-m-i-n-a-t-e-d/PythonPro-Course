MANAGE_PY = r'''
#!/usr/bin/env python
import os
import sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
from django.core.management import execute_from_command_line
execute_from_command_line(sys.argv)
'''

SETTINGS = r'''
import os
SECRET_KEY = "school-demo-key"
DEBUG = True
ALLOWED_HOSTS = ["*"]
ROOT_URLCONF = "config.urls"
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "reports",
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "app"),
        "USER": os.getenv("POSTGRES_USER", "app"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "demo_password"),
        "HOST": "database",
        "PORT": "5432",
    }
}
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")
USE_TZ = True
'''

CELERY_APP = r'''
import os
from celery import Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
'''

CONFIG_INIT = r'''
from .celery import app as celery_app
__all__ = ("celery_app",)
'''

REPORTS_INIT = ""

TASKS = r'''
import time
from celery import shared_task

@shared_task
def generate_report(title):
    time.sleep(3)
    return {"title": title, "status": "generated"}
'''

URLS = r'''
import json
from celery.result import AsyncResult
from django.db import connection
from django.http import JsonResponse
from django.urls import path
from reports.tasks import generate_report

def create_report(request):
    if request.method != "POST":
        return JsonResponse({"detail": "POST required"}, status=405)
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    data = json.loads(request.body or b"{}")
    task = generate_report.delay(data.get("title", "Report"))
    return JsonResponse({"task_id": task.id}, status=202)

def report_status(request, task_id):
    task = AsyncResult(task_id)
    return JsonResponse({"state": task.state, "result": task.result if task.successful() else None})

urlpatterns = [
    path("reports/", create_report),
    path("reports/<str:task_id>/", report_status),
]
'''

DOCKERFILE = r'''
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir django celery redis "psycopg[binary]" gunicorn
COPY . .
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
'''

WSGI = r'''
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()
'''

COMPOSE = r'''
services:
  backend:
    build: ./backend
    command: sh -c "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000"
    environment: &app-env
      POSTGRES_DB: app
      POSTGRES_USER: app
      POSTGRES_PASSWORD: demo_password
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/1
    depends_on:
      database:
        condition: service_healthy
      redis:
        condition: service_healthy
    ports:
      - "127.0.0.1:8000:8000"

  celery-worker:
    build: ./backend
    command: celery -A config worker --loglevel=info
    environment: *app-env
    depends_on:
      database:
        condition: service_healthy
      redis:
        condition: service_healthy

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 3s
      timeout: 2s
      retries: 10

  database:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: app
      POSTGRES_PASSWORD: demo_password
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d app"]
      interval: 5s
      timeout: 3s
      retries: 10
    volumes:
      - postgres-data:/var/lib/postgresql/data

volumes:
  postgres-data:
'''
