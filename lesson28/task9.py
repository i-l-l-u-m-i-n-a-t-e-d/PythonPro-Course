# tasks_app/management/commands/enqueue_tasks.py
import random

from django.core.management.base import BaseCommand

from tasks_app.tasks import multiply


class Command(BaseCommand):
    help = 'Dodaje do kolejki 50 zadan multiply z losowymi argumentami.'

    def handle(self, *args, **options):
        task_ids = []
        for _ in range(50):
            a = random.randint(1, 20)
            b = random.randint(1, 20)
            task = multiply.delay(a, b)
            task_ids.append(task.id)
            self.stdout.write(f'Dodano multiply({a}, {b}) task_id={task.id}')
        self.stdout.write(self.style.SUCCESS(f'Dodano lacznie {len(task_ids)} zadan.'))


