# library/serializers.py
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Author, Book, Copy, Genre, Reservation


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ('id', 'full_name', 'photo')


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ('id', 'name')


class CopySerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source='book.title', read_only=True)

    class Meta:
        model = Copy
        fields = ('id', 'book', 'book_title', 'inventory_number', 'status')


class BookSerializer(serializers.ModelSerializer):
    authors = AuthorSerializer(many=True, read_only=True)
    genres = GenreSerializer(many=True, read_only=True)
    available_copies = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = (
            'id',
            'title',
            'description',
            'publication_date',
            'cover',
            'authors',
            'genres',
            'available_copies',
        )

    @extend_schema_field(OpenApiTypes.INT)
    def get_available_copies(self, obj):
        return obj.copies.filter(status=Copy.Status.AVAILABLE).count()


class ReservationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    book_title = serializers.CharField(source='copy.book.title', read_only=True)
    copy_inventory_number = serializers.CharField(source='copy.inventory_number', read_only=True)

    class Meta:
        model = Reservation
        fields = (
            'id',
            'username',
            'book_title',
            'copy_inventory_number',
            'reservation_date',
            'valid_until',
            'status',
        )


# library/api.py
class BookViewSet(viewsets.ReadOnlyModelViewSet):
    """Endpointy tylko do odczytu dla publicznego katalogu książek BiblioTech."""

    serializer_class = BookSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Book.objects.prefetch_related('authors', 'genres', 'copies')
        search = self.request.query_params.get('search', '').strip()
        author = self.request.query_params.get('author', '').strip()
        genre = self.request.query_params.get('genre', '').strip()
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(authors__full_name__icontains=search)
                | Q(genres__name__icontains=search)
            )
        if author:
            queryset = queryset.filter(authors__id=author)
        if genre:
            queryset = queryset.filter(genres__id=genre)
        return queryset.distinct().order_by('title')


class AuthorViewSet(viewsets.ReadOnlyModelViewSet):
    """Endpointy tylko do odczytu dla autorów."""

    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [permissions.AllowAny]


class GenreViewSet(viewsets.ReadOnlyModelViewSet):
    """Endpointy tylko do odczytu dla gatunków książek."""

    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [permissions.AllowAny]


class CopyViewSet(viewsets.ReadOnlyModelViewSet):
    """Endpointy tylko do odczytu dla egzemplarzy i ich dostępności."""

    serializer_class = CopySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Copy.objects.select_related('book')
        status = self.request.query_params.get('status', '').strip()
        if status:
            queryset = queryset.filter(status=status)
        return queryset


class ReservationViewSet(viewsets.ReadOnlyModelViewSet):
    """Chronione endpointy tylko do odczytu dla rezerwacji zalogowanego użytkownika."""

    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False) or not self.request.user.is_authenticated:
            return Reservation.objects.none()
        return Reservation.objects.filter(user=self.request.user).select_related('user', 'copy__book')


# library/api_urls.py
router = DefaultRouter()
router.register('books', BookViewSet, basename='book')
router.register('authors', AuthorViewSet, basename='author')
router.register('genres', GenreViewSet, basename='genre')
router.register('copies', CopyViewSet, basename='copy')
router.register('reservations', ReservationViewSet, basename='reservation')

urlpatterns = [
    path('', include(router.urls)),
]
