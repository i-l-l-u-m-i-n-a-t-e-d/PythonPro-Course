INIT_SCRIPT = r'''
#!/bin/sh
set -eu

until python manage.py check --database default >/dev/null 2>&1; do
  echo "Waiting for database..."
  sleep 1
done

python manage.py migrate --noinput
python manage.py shell -c "import os; from django.contrib.auth import get_user_model; U=get_user_model(); u=U.objects.filter(username='admin').first(); u or U.objects.create_superuser('admin', 'admin@example.com', os.environ['DJANGO_SUPERUSER_PASSWORD'])"
'''

ENTRYPOINT = r'''
#!/bin/sh
set -eu
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000
'''

COMPOSE = r'''
services:
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

  init:
    build: ./backend
    entrypoint: ["sh", "/app/init.sh"]
    environment: &app-env
      POSTGRES_DB: app
      POSTGRES_USER: app
      POSTGRES_PASSWORD: demo_password
      DJANGO_SUPERUSER_PASSWORD: demo_password
    depends_on:
      database:
        condition: service_healthy

  backend:
    build: ./backend
    entrypoint: ["sh", "/app/entrypoint.sh"]
    environment: *app-env
    depends_on:
      init:
        condition: service_completed_successfully
    ports:
      - "127.0.0.1:8000:8000"

volumes:
  postgres-data:
'''
