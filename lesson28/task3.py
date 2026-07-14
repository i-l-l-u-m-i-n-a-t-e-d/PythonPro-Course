# tasks_app/tasks.py
from django.conf import settings
from django.utils import timezone
from celery import shared_task


@shared_task
def log_timestamp():
    log_path = settings.BASE_DIR / 'log.txt'
    now_text = timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M:%S %Z')
    with log_path.open('a', encoding='utf-8') as log_file:
        log_file.write(f'{now_text}\n')
    print(f'Zapisano timestamp: {now_text}')
    return str(log_path)



