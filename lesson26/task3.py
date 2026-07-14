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

# api/urls.py
urlpatterns = [
    path('cached-products/', cached_product_list, name='cached-product-list'),
    path('selective-cache/', selective_cache_view, name='selective-cache'),
]

