# api/services.py
def product_detail_cache_key(product_id):
    return f'lesson27:product_detail:{product_id}'

# api/views.py
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @method_decorator(cache_page(60 * 10))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        product = self.get_object()
        cache_key = product_detail_cache_key(product.pk)
        cached_data = cache.get(cache_key)

        if cached_data is None:
            cached_data = dict(self.get_serializer(product).data)
            cache.set(cache_key, cached_data, timeout=60)
            cache_status = 'miss'
        else:
            cache_status = 'hit'

        response_data = dict(cached_data)
        response_data['detail_cache'] = cache_status
        return Response(response_data)

    def perform_update(self, serializer):
        instance = serializer.save()
        cache.delete(product_detail_cache_key(instance.pk))


