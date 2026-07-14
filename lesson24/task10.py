# api/serializers.py
class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ["id", "title", "content", "created_at"]

    def validate_title(self, value):
        if len(value) < 5:
            raise serializers.ValidationError("Tytuł musi mieć co najmniej 5 znaków.")
        return value


"""
Przykład błędnego POST:

POST /api/notes/
{
    "title": "abc",
    "content": "Za krótki tytuł"
}

Oczekiwany błąd:
{
    "title": ["Tytuł musi mieć co najmniej 5 znaków."]
}
"""
