# config/settings.py
CACHE_DIR = BASE_DIR / 'django_cache'

if CACHE_MODE == 'filebased':
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': str(CACHE_DIR),
        }
    }

# api/views.py
@cache_page(60)
@api_view(['GET'])
def cached_product_list(request):
    products = Product.objects.all()
    serializer = ProductSerializer(products, many=True)
    return Response(
        {
            'generated_at': timezone.now().isoformat(),
            'cache_note': 'This whole response is cached for 60 seconds.',
            'products': serializer.data,
        }
    )


