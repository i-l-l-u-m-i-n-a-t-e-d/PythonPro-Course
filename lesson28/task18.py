# config/settings.py
from kombu import Queue


CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_TASK_QUEUES = (
    Queue('default'),
    Queue('priority_queue'),
)
CELERY_TASK_ROUTES = {
    'tasks_app.tasks.send_priority_email': {'queue': 'priority_queue'},
}


# tasks_app/tasks.py
import time
from celery import shared_task


@shared_task(queue='priority_queue')
def send_priority_email(recipient_email, subject='Pilne powiadomienie', body='Wazna wiadomosc'):
    print(f'[priority_queue] Wysylanie maila do {recipient_email}: {subject}')
    time.sleep(1)
    return {'recipient_email': recipient_email, 'subject': subject, 'sent': True}


# tasks_app/views.py
def send_priority_email_view(request):
    recipient_email = request.POST.get('recipient_email', 'priority@example.com')
    task = send_priority_email.apply_async(args=[recipient_email], queue='priority_queue')
    return JsonResponse({'message': 'Priorytetowy mail dodany do priority_queue', 'task_id': task.id})



