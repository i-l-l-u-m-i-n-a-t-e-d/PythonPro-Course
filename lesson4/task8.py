imiona = ["Anna", "Jan", "Piotr", "Kasia"]

name = input("Podaj imie do wyszukania: ").strip().capitalize()



for i in imiona:

    if name == i:

        print("Znaleziono!")
        break

else:

    print("Nie znaleziono imienia na liście.")
