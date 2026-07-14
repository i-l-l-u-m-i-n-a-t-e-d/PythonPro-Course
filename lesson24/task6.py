# api/models.py
class Note(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


# api/serializers.py
class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ["id", "title", "content", "created_at"]

    def validate_title(self, value):
        if len(value) < 5:
            raise serializers.ValidationError("Tytuł musi mieć co najmniej 5 znaków.")
        return value


# api/views.py
class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all().order_by("-created_at")
    serializer_class = NoteSerializer


# config/urls.py
router.register(r'notes', views.NoteViewSet)



