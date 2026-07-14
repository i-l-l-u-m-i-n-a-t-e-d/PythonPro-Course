# api/services.py
EXPENSIVE_CALCULATION_KEY = 'lesson27:expensive_calculation'


def get_expensive_calculation_result():
    cached_result = cache.get(EXPENSIVE_CALCULATION_KEY)
    if cached_result is not None:
        result = dict(cached_result)
        result['source'] = 'cache'
        result['cache_hit'] = True
        return result

    time.sleep(settings.EXPENSIVE_CALCULATION_SECONDS)
    result = {
        'value': 42,
        'source': 'calculated_live',
        'cache_hit': False,
    }
    cache.set(EXPENSIVE_CALCULATION_KEY, result, timeout=60 * 60)
    return dict(result)

# api/views.py
@api_view(['GET'])
def selective_cache_view(request):
    fast_product_count = Product.objects.count()
    expensive_result = get_expensive_calculation_result()
    return Response(
        {
            'fast_database_query': {
                'product_count': fast_product_count,
                'note': 'This database value is read on every request.',
            },
            'expensive_calculation': expensive_result,
        }
    )

# api/urls.py
urlpatterns = [
    path('cached-products/', cached_product_list, name='cached-product-list'),
    path('selective-cache/', selective_cache_view, name='selective-cache'),
]


