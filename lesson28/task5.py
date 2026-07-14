# tasks_app/tasks.py
from django.contrib.auth import get_user_model
from celery import shared_task


@shared_task
def count_users():
    User = get_user_model()
    count = User.objects.count()
    print(f'Liczba uzytkownikow: {count}')
    return count

