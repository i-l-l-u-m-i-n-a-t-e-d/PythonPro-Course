# api/views.py
class Task8ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @method_decorator(cache_page(60 * 10))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @method_decorator(cache_page(60))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

# api/urls.py
router = DefaultRouter()
router.register('products', ProductViewSet, basename='product')
router.register('task8-products', Task8ProductViewSet, basename='task8-product')

