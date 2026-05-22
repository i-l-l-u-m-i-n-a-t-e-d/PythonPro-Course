class Telewizor:

    def __init__(self):

        self.__kanal = 1
        self.__glosnosc = 10
        self.__wlaczony = False

    def wlacz(self):

        self.__wlaczony = True

    def wylacz(self):

        self.__wlaczony = False

    def zmien_kanal(self, numer):

        if self.__wlaczony:

            self.__kanal = numer

        else:

            print("Telewizor jest wyłączony. Nie można zmienić kanału.")

    def glosniej(self):

        if not self.__wlaczony:

            print("Telewizor jest wyłączony. Nie można zmienić głośności.")

        elif self.__glosnosc < 100:

            self.__glosnosc += 1

        else:
            print("Głośność jest już maksymalna.")

    def ciszej(self):

        if not self.__wlaczony:

            print("Telewizor jest wyłączony. Nie można zmienić głośności.")

        elif self.__glosnosc > 0:

            self.__glosnosc -= 1

        else:

            print("Głośność jest już minimalna.")

    def info(self):

        stan = "włączony" if self.__wlaczony else "wyłączony"

        print(f"Stan: {stan}, kanał: {self.__kanal}, głośność: {self.__glosnosc}")


tv = Telewizor()

tv.zmien_kanal(5)   

tv.wlacz()
tv.zmien_kanal(54)

for _ in range(95):
    tv.glosniej()

tv.glosniej()       
tv.info()