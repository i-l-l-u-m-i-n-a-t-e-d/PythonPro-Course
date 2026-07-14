# tasks_app/tasks.py
import random
from celery import chain, shared_task
from django.conf import settings


@shared_task
def generate_random_number():
    return random.randint(1, 10)


@shared_task
def multiply_by_10(number):
    return int(number) * 10


@shared_task
def save_chain_result_to_file(number):
    output_path = settings.MEDIA_ROOT / 'chain_results.txt'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('a', encoding='utf-8') as output_file:
        output_file.write(f'Wynik lancucha: {number}\n')
    return {'result': number, 'path': str(output_path)}


def build_number_chain():
    return chain(generate_random_number.s(), multiply_by_10.s(), save_chain_result_to_file.s())


# tasks_app/views.py
def run_chain(request):
    task = build_number_chain().apply_async()
    return JsonResponse({'message': 'Lancuch zadan uruchomiony', 'task_id': task.id})


# tasks_app/urls.py
urlpatterns = [
    path('run-chain/', views.run_chain, name='run_chain'),
]


