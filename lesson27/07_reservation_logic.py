# library/services.py
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import Book, Copy, Reservation


class ReservationError(Exception):
    pass


@transaction.atomic
def reserve_available_copy(user, book_id):
    book = Book.objects.select_for_update().get(pk=book_id)
    copy = (
        Copy.objects.select_for_update()
        .filter(book=book, status=Copy.Status.AVAILABLE)
        .order_by('inventory_number')
        .first()
    )
    if copy is None:
        raise ReservationError('Brak dostępnego egzemplarza tej książki.')

    copy.status = Copy.Status.RESERVED
    copy.save(update_fields=['status'])
    return Reservation.objects.create(
        user=user,
        copy=copy,
        valid_until=timezone.localdate() + timedelta(days=14),
    )
