# tasks_app/tasks.py
from celery import shared_task


@shared_task
def hello_world():
    print('Hello from Celery!')
    return 'Hello from Celery!'


# tasks_app/views.py
from django.http import JsonResponse
from .tasks import hello_world


def hello_celery(request):
    task = hello_world.delay()
    return JsonResponse({'message': 'Zadanie hello_world dodane do kolejki', 'task_id': task.id})


# tasks_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('hello-celery/', views.hello_celery, name='hello_celery'),
]


