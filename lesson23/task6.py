# users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


# users/views.py
from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import CustomUserCreationForm


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                f'Konto dla {user.username} zostalo utworzone i jestes zalogowany.',
            )
            return redirect('home')
    else:
        form = CustomUserCreationForm()

    return render(request, 'users/register.html', {'form': form})
