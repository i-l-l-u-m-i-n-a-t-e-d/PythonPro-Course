# tasks_app/tasks.py
from celery import shared_task


@shared_task
def multiply(a, b):
    return int(a) * int(b)


# tasks_app/forms.py
from django import forms


class MultiplyForm(forms.Form):
    a = forms.IntegerField(label='Pierwsza liczba')
    b = forms.IntegerField(label='Druga liczba')


# tasks_app/views.py
from django.http import HttpResponse
from django.shortcuts import render
from .forms import MultiplyForm
from .tasks import multiply


def multiply_view(request):
    form = MultiplyForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        task = multiply.delay(form.cleaned_data['a'], form.cleaned_data['b'])
        return HttpResponse(f'Zadanie multiply dodane do kolejki. task_id={task.id}')
    return render(request, 'tasks_app/multiply.html', {'form': form})


# tasks_app/urls.py
urlpatterns = [
    path('multiply/', views.multiply_view, name='multiply'),
]


# templates/tasks_app/multiply.html
"""
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Wyślij do Celery</button>
</form>
"""


