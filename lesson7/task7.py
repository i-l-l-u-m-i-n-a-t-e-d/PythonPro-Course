# wersja 1 - z .get()

def pobierz_wartosc(slownik, klucz):
    return slownik.get(klucz)


slownik = {
    "imie": "Anna",
    "wiek": 28,
    "miejscowosc": "Warszawa",
    "status_studenta": False
}

r = pobierz_wartosc(slownik, "status_studenta")

print(r)


# wersja 2 - z try...except KeyError

def pobierz_wartosc_try(slownik, klucz):

    try:
        return slownik[klucz]

    except KeyError:
        return None


r = pobierz_wartosc_try(slownik, "status_studenta")

print(r)
