# tasks_app/models.py
from django.db import models


class EmailNotification(models.Model):
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


# tasks_app/tasks.py
import time
from django.utils import timezone
from celery import shared_task
from .models import EmailNotification


@shared_task
def send_email_notification(notification_id):
    notification = EmailNotification.objects.get(pk=notification_id)
    print(f'Wysylanie maila do {notification.recipient_email}: {notification.subject}')
    time.sleep(1)
    notification.sent_at = timezone.now()
    notification.save(update_fields=['sent_at'])
    print('Mail zostal wyslany.')
    return notification.sent_at.isoformat()


# tasks_app/views.py
def send_email_notification_view(request):
    notification = EmailNotification.objects.create(
        recipient_email=request.POST.get('recipient_email', 'student@example.com'),
        subject=request.POST.get('subject', 'Powiadomienie z Celery'),
        body=request.POST.get('body', 'To jest testowa tresc maila.'),
    )
    task = send_email_notification.delay(notification.id)
    return JsonResponse({'notification_id': notification.id, 'task_id': task.id})


