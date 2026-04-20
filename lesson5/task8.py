def stworz_profil(imie, **dane_dodatkowe):

    dict = {}

    dict["imie"] = imie



    for i in dane_dodatkowe: 
        
        # print(i) keys
        # print(dane_dodatkowe[i]) values

        dict[i] = dane_dodatkowe[i]


    return dict


result = stworz_profil("Grok", wiek= 15, miasto="Poznań", wzrost=190, waga=123)

print(result)