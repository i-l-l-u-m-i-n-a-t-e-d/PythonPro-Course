imiona = ["Anna", "Jan", "Piotr", "Kasia"]

name = input("Podaj imie do wyszukania ").strip().capitalize()



#for-else

for i in imiona:

    if name == i:

        print("Znaleziono!")
        not_found = False
        break


else:
    print("Nie znaleziono imienia na liście.")









