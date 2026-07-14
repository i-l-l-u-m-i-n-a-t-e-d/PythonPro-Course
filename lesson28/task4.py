# config/settings.py
CELERY_BEAT_SCHEDULE = {
    'log-timestamp-every-10-seconds': {
        'task': 'tasks_app.tasks.log_timestamp',
        'schedule': 10.0,
    },
}


