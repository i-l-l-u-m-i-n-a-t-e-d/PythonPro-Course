

class BladPrzetwarzaniaDanychError(Exception):
    pass

def przetworz_dane(dane: dict):

    try:

       

        print(dane["wiek"])

    except KeyError as k:

        print(f"Loguję błąd: {k}")

        raise BladPrzetwarzaniaDanychError(f"Wpisany klucz {k}, nie istnieje w tym slowniku.")


dict = {
    "imie": "Robert", 
    "nazwisko": "Lewandowski", 
    "obecny klub": "Barcelona"}

przetworz_dane(dict)