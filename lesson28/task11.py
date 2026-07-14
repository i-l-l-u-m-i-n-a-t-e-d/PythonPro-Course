# tasks_app/tasks.py
import time
from celery import shared_task


@shared_task(bind=True)
def progress_counter(self):
    for i in range(1, 101):
        time.sleep(0.1)
        self.update_state(state='PROGRESS', meta={'current': i, 'total': 100})
    return {'current': 100, 'total': 100, 'status': 'Zadanie zakonczone'}


# tasks_app/views.py
from celery.result import AsyncResult
from django.http import JsonResponse


def start_progress_task(request):
    task = progress_counter.delay()
    return JsonResponse({'message': 'Zadanie postepu uruchomione', 'task_id': task.id})


def task_status(request, task_id):
    result = AsyncResult(task_id)
    response = {'task_id': task_id, 'state': result.state, 'current': 0, 'total': 1, 'percent': 0, 'result': None}
    if result.state == 'PROGRESS' and isinstance(result.info, dict):
        current = result.info.get('current', 0)
        total = result.info.get('total', 100)
        response.update({'current': current, 'total': total, 'percent': round(current / total * 100, 2)})
    elif result.successful():
        response.update({'current': 1, 'total': 1, 'percent': 100, 'result': result.result})
    return JsonResponse(response)


# tasks_app/urls.py
urlpatterns = [
    path('start-progress/', views.start_progress_task, name='start_progress'),
    path('task-status/<str:task_id>/', views.task_status, name='task_status'),
]


