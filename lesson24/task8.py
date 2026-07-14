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


# Testowany adres:
# /api/products/?min_price=100&max_price=200
# Odpowiedź dla danych testowych:
# [{"id": 2, "name": "Klawiatura", "price": "150.00"}]
