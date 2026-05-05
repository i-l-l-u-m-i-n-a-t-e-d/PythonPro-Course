#version with .get()


# def pobierz_wartosc(slownik, klucz):

#     return slownik.get(klucz)

# dict = {
#     "imie": "Anna",
#     "wiek": 28,
#     "miejscowosc": "Warszawa",
#     "status_studenta": False
# }

# r = pobierz_wartosc(dict, "")

# print(r)

def pobierz_wartosc(slownik, klucz):

    try:

        return slownik[klucz]

    except KeyError:

        return None

  

dict = {
    "imie": "Anna",
    "wiek": 28,
    "miejscowosc": "Warszawa",
    "status_studenta": False
}

r = pobierz_wartosc(dict, "status_studenta")

print(r)