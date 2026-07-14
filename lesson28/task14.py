# tasks_app/tasks.py
import csv
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from celery import shared_task


@shared_task
def generate_users_csv():
    User = get_user_model()
    reports_dir = settings.MEDIA_ROOT / 'reports'
    reports_dir.mkdir(parents=True, exist_ok=True)
    filename = f'users_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv'
    file_path = reports_dir / filename
    with file_path.open('w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['id', 'username', 'email'])
        for user in User.objects.order_by('id'):
            writer.writerow([user.id, user.get_username(), user.email])
    return {'path': str(file_path), 'url': f'{settings.MEDIA_URL}reports/{filename}'}


# tasks_app/views.py
def generate_users_csv_view(request):
    task = generate_users_csv.delay()
    return JsonResponse({'message': 'Generowanie CSV uruchomione', 'task_id': task.id})


def csv_status(request, task_id):
    result = AsyncResult(task_id)
    response = {'task_id': task_id, 'state': result.state, 'ready': result.ready()}
    if result.successful():
        data = result.result
        response.update({'path': data.get('path'), 'download_url': data.get('url')})
    return JsonResponse(response)


# tasks_app/urls.py
urlpatterns = [
    path('generate-users-csv/', views.generate_users_csv_view, name='generate_users_csv'),
    path('csv-status/<str:task_id>/', views.csv_status, name='csv_status'),
]


