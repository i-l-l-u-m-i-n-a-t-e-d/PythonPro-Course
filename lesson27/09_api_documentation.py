# config/settings.py
INSTALLED_APPS = [
    'rest_framework',
    'drf_spectacular',
    'drf_spectacular_sidecar',
    'library',
]

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'API BiblioTech',
    'DESCRIPTION': (
        'API katalogu bibliotecznego i rezerwacji udokumentowane za pomocą '
        'OpenAPI, Swagger UI, ReDoc oraz drf-spectacular.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST': 'SIDECAR',
}


# config/urls.py
urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/schema/swagger-ui/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),
    path(
        'api/schema/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc',
    ),
]


# library/api.py
@extend_schema_view(
    list=extend_schema(
        summary='Lista książek',
        description='Zwraca książki z katalogu. Obsługuje wyszukiwanie tekstowe oraz filtrowanie po autorze lub gatunku.',
        tags=['Książki'],
        parameters=[
            OpenApiParameter(
                name='search',
                description='Wyszukiwanie w tytule, opisie, nazwach autorów i nazwach gatunków.',
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name='author',
                description='Filtrowanie książek według identyfikatora autora.',
                required=False,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name='genre',
                description='Filtrowanie książek według identyfikatora gatunku.',
                required=False,
                type=OpenApiTypes.INT,
            ),
        ],
        responses={200: BookSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary='Szczegóły jednej książki',
        tags=['Książki'],
        responses={
            200: BookSerializer,
            404: OpenApiResponse(description='Nie znaleziono książki.'),
        },
    ),
)
class BookViewSet(viewsets.ReadOnlyModelViewSet):
    """Endpointy tylko do odczytu dla publicznego katalogu książek BiblioTech."""
