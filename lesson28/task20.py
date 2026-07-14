# tasks_app/models.py
class TransactionRecord(models.Model):
    name = models.CharField(max_length=100)
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)


# tasks_app/tasks.py
from django.utils import timezone
from celery import shared_task
from .models import TransactionRecord


@shared_task
def process_transaction_record(record_id):
    record = TransactionRecord.objects.get(pk=record_id)
    record.processed = True
    record.processed_at = timezone.now()
    record.save(update_fields=['processed', 'processed_at'])
    return f'Przetworzono TransactionRecord id={record_id}'


# tasks_app/views.py
from types import SimpleNamespace
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone


def transaction_task(request):
    record_name = request.POST.get('name') or f'Rekord {timezone.now().strftime("%H:%M:%S")}'
    task_holder = SimpleNamespace(task_id=None)
    with transaction.atomic():
        record = TransactionRecord.objects.create(name=record_name)

        def enqueue_after_commit():
            task = process_transaction_record.delay(record.id)
            task_holder.task_id = task.id

        transaction.on_commit(enqueue_after_commit)
    return JsonResponse({
        'record_id': record.id,
        'task_id': task_holder.task_id,
        'message': 'Zadanie zostalo zaplanowane przez transaction.on_commit',
    })


