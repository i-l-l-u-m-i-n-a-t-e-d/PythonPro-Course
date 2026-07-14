# config/settings.py
from datetime import timedelta


SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(seconds=10),
}


"""
Sprawdzenie w Postmanie:

1. Wysłałem POST na /auth/jwt/create/ i otrzymałem nowy access token.
2. Użyłem go od razu w żądaniu GET do /api/protected/.
   Odpowiedź: 200 OK
   {"username": "student1"}
3. Odczekałem około 12 sekund i ponowiłem to samo żądanie z tym samym tokenem.

Za drugim razem serwer zwrócił status 401 Unauthorized:
{
  "detail": "Given token not valid for any token type",
  "code": "token_not_valid",
  "messages": [
    {
      "token_class": "AccessToken",
      "token_type": "access",
      "message": "Token is expired"
    }
  ]
}

Po ponownym zalogowaniu otrzymałem nowy access token, który znowu działał przez 10 sekund.
"""
