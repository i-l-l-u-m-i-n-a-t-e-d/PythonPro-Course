# tasks_app/tasks.py
import time
from celery import shared_task


@shared_task
def process_video_task():
    print('Start przetwarzania wideo...')
    time.sleep(15)
    print('Przetwarzanie wideo zakonczone.')
    return 'Wideo przetworzone'


# tasks_app/views.py
from django.http import HttpResponse
from .tasks import process_video_task


def process_video(request):
    process_video_task.delay()
    return HttpResponse('Przetwarzanie wideo rozpoczęte!')


# tasks_app/urls.py
urlpatterns = [
    path('process-video/', views.process_video, name='process_video'),
]


