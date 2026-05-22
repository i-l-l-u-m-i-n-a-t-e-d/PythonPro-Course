class Uzytkownik:

    def __init__(self, wiek):

        self._wiek = 0
        self.wiek = wiek

    @property
    def wiek(self):

        return self._wiek

    @wiek.setter
    def wiek(self, nowy_wiek):

        if 0 <= nowy_wiek <= 120:

            self._wiek = nowy_wiek

        else:
            
            print("Błąd: wiek musi być w zakresie od 0 do 120.")


user = Uzytkownik(25)
print(user.wiek)

user.wiek = 150
print(user.wiek)