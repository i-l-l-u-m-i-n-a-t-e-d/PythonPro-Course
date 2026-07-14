# library/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=False, label='Adres e-mail')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


# library/views.py
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, TemplateView

from .forms import RegisterForm
from .models import Author, Book, Copy, Genre, Reservation
from .services import ReservationError, reserve_available_copy


class HomeView(TemplateView):
    template_name = 'library/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['latest_books'] = (
            Book.objects.prefetch_related('authors', 'genres')
            .annotate(available_count=Count('copies', filter=Q(copies__status=Copy.Status.AVAILABLE)))
            .order_by('-publication_date')[:6]
        )
        context['book_count'] = Book.objects.count()
        context['author_count'] = Author.objects.count()
        context['genre_count'] = Genre.objects.count()
        return context


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        messages.success(self.request, 'Konto zostało utworzone. Możesz się teraz zalogować.')
        return super().form_valid(form)


class BiblioLoginView(LoginView):
    template_name = 'registration/login.html'


class BookListView(ListView):
    model = Book
    template_name = 'library/book_list.html'
    context_object_name = 'books'
    paginate_by = 12

    def get_queryset(self):
        queryset = Book.objects.prefetch_related('authors', 'genres').annotate(
            available_count=Count('copies', filter=Q(copies__status=Copy.Status.AVAILABLE))
        )
        query = self.request.GET.get('q', '').strip()
        author = self.request.GET.get('author', '').strip()
        genre = self.request.GET.get('genre', '').strip()
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(authors__full_name__icontains=query)
                | Q(genres__name__icontains=query)
            )
        if author:
            queryset = queryset.filter(authors__id=author)
        if genre:
            queryset = queryset.filter(genres__id=genre)
        return queryset.distinct().order_by('title')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['authors'] = Author.objects.all()
        context['genres'] = Genre.objects.all()
        context['search_query'] = self.request.GET.get('q', '').strip()
        context['selected_author'] = self.request.GET.get('author', '').strip()
        context['selected_genre'] = self.request.GET.get('genre', '').strip()
        return context


class BookDetailView(DetailView):
    model = Book
    template_name = 'library/book_detail.html'
    context_object_name = 'book'

    def get_queryset(self):
        return Book.objects.prefetch_related('authors', 'genres', 'copies')


class UserReservationsView(LoginRequiredMixin, ListView):
    model = Reservation
    template_name = 'library/reservations.html'
    context_object_name = 'reservations'

    def get_queryset(self):
        return Reservation.objects.filter(user=self.request.user).select_related('copy__book')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reservations = context['reservations']
        today = timezone.localdate()
        context['current_reservations'] = reservations.filter(
            status=Reservation.Status.ACTIVE,
            valid_until__gte=today,
        )
        context['historical_reservations'] = reservations.exclude(
            status=Reservation.Status.ACTIVE,
            valid_until__gte=today,
        )
        return context


@require_POST
def reserve_book(request, pk):
    if not request.user.is_authenticated:
        return redirect(f"{reverse_lazy('login')}?next={request.path}")
    book = get_object_or_404(Book, pk=pk)
    try:
        reserve_available_copy(request.user, book.pk)
    except ReservationError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f'Książka „{book.title}” została zarezerwowana na 14 dni.')
    return redirect('book_detail', pk=book.pk)


# library/urls.py
urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('books/', BookListView.as_view(), name='book_list'),
    path('books/<int:pk>/', BookDetailView.as_view(), name='book_detail'),
    path('books/<int:pk>/reserve/', reserve_book, name='reserve_book'),
    path('reservations/', UserReservationsView.as_view(), name='my_reservations'),
    path('accounts/login/', BiblioLoginView.as_view(), name='login'),
    path('accounts/register/', RegisterView.as_view(), name='register'),
    path('accounts/logout/', LogoutView.as_view(next_page='home'), name='logout'),
]
