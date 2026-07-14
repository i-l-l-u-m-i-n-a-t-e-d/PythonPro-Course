# tasks_app/models.py
from django.db import models
from django.utils import timezone


class LogEntry(models.Model):
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)


# tasks_app/tasks.py
from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from .models import LogEntry


@shared_task
def cleanup_old_logs():
    cutoff = timezone.now() - timedelta(days=90)
    deleted_count, _ = LogEntry.objects.filter(created_at__lt=cutoff).delete()
    print(f'Usunieto stare logi: {deleted_count}')
    return deleted_count


# config/settings.py
CELERY_BEAT_SCHEDULE = {
    'cleanup-old-logs-daily': {
        'task': 'tasks_app.tasks.cleanup_old_logs',
        'schedule': crontab(hour=2, minute=30),
    },
}


