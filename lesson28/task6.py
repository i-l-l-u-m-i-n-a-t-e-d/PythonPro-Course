# config/settings.py
from celery.schedules import crontab


CELERY_BEAT_SCHEDULE = {
    'count-users-daily-2300': {
        'task': 'tasks_app.tasks.count_users',
        'schedule': crontab(hour=23, minute=0),
    },
}



