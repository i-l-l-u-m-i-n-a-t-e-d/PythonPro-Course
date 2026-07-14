# api/views.py
class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer

    def get_queryset(self):
        queryset = Product.objects.all().order_by("id")
        min_price = self.request.query_params.get("min_price")
        max_price = self.request.query_params.get("max_price")

        try:
            if min_price:
                queryset = queryset.filter(price__gte=Decimal(min_price))
            if max_price:
                queryset = queryset.filter(price__lte=Decimal(max_price))
        except (InvalidOperation, ValueError):
            return Product.objects.none()

        return queryset


# config/urls.py
router = DefaultRouter()
router.register(r'products', views.ProductViewSet, basename='product')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
]


"""
Po wejściu na /api/products/ widać endpoint DRF dla produktów.
GET zwraca listę produktów, a POST pozwala dodać nowy produkt.
"""
