# tasks_app/tasks.py
import requests
from celery import shared_task


@shared_task(bind=True)
def retry_nonexistent_url(self):
    try:
        response = requests.get('https://this-domain-should-not-exist.invalid', timeout=5)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise self.retry(exc=exc, countdown=60, max_retries=3)
    return 'Polaczenie udane'


