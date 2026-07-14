# tasks_app/tasks.py
from django.contrib.auth import get_user_model
from django.utils import timezone
from celery import shared_task


@shared_task
def update_user_last_login(user_id):
    User = get_user_model()
    user = User.objects.get(pk=user_id)
    user.last_login = timezone.now()
    user.save(update_fields=['last_login'])
    return f'Zaktualizowano last_login dla user_id={user_id}'


# tasks_app/views.py
def update_last_login_view(request, user_id):
    task = update_user_last_login.delay(user_id)
    return JsonResponse({'message': 'Aktualizacja last_login dodana do kolejki', 'task_id': task.id})


# tasks_app/urls.py
urlpatterns = [
    path('update-last-login/<int:user_id>/', views.update_last_login_view, name='update_last_login'),
]



