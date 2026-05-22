class RejestracjaUzytkownika:

    def __init__(self, email, haslo):

        if "@" not in email:

            raise ValueError("Podano niepoprawny adres email.")

        if len(haslo) < 8:

            raise ValueError("Hasło musi mieć co najmniej 8 znaków.")

        self.email = email
        self.haslo = haslo


dane_testowe = [

    ("romek@gmail.com", "Password123"),
    ("romekgmail.com", "Password123"),
    ("romek@gmail.com", "Pass")
]

for email, haslo in dane_testowe:

    try:
        user = RejestracjaUzytkownika(email, haslo)

        print(f"Utworzono użytkownika: {user.email}")

    except ValueError as e:
        
        print(f"Błąd: {e}")