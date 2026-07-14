# api/models.py
class Author(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=200)
    publication_year = models.PositiveIntegerField()
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="books")

    def __str__(self):
        return f"{self.title} - {self.author.name}"


# api/serializers.py
class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ["id", "name"]


class BookSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)
    author_id = serializers.PrimaryKeyRelatedField(
        queryset=Author.objects.all(),
        source="author",
        write_only=True,
    )

    class Meta:
        model = Book
        fields = ["id", "title", "publication_year", "author", "author_id"]


# api/views.py
class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all().order_by("id")
    serializer_class = AuthorSerializer


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.select_related("author").all().order_by("id")
    serializer_class = BookSerializer


# config/urls.py
router.register(r'authors', views.AuthorViewSet)
router.register(r'books', views.BookViewSet)


# BookSerializer pokazuje nazwę autora:
# {"id": 1, "title": "Pan Tadeusz", "publication_year": 1834, "author": "Adam Mickiewicz"}
