# tasks_app/models.py
class ScrapedPageTitle(models.Model):
    url = models.URLField()
    title = models.CharField(max_length=255)
    scraped_at = models.DateTimeField(auto_now_add=True)


# tasks_app/tasks.py
import requests
from bs4 import BeautifulSoup
from celery import shared_task
from .models import ScrapedPageTitle


@shared_task
def scrape_example_title():
    url = 'https://example.com'
    response = requests.get(url, timeout=(5, 30))
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    title = soup.title.string.strip() if soup.title and soup.title.string else 'Brak tytulu'
    ScrapedPageTitle.objects.create(url=url, title=title)
    return title


# config/settings.py
CELERY_BEAT_SCHEDULE = {
    'scrape-example-title-hourly': {
        'task': 'tasks_app.tasks.scrape_example_title',
        'schedule': crontab(minute=0),
    },
}



