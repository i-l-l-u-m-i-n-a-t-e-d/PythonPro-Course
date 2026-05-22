class Instrument:

    def graj(self):
        
        return "Wydaje dźwięk."


class Strunowy(Instrument):

    def graj(self):

        return super().graj() + " [Szarpnięcie struny]"


class Dety(Instrument):

    def graj(self):

        return super().graj() + " [Wibrowanie powietrza]"


class Gitara(Strunowy):

    def graj(self):

        return super().graj() + " [Akord G-dur]"


class Trabka(Dety):

    def graj(self):

        return super().graj() + " [Akord A-dur]"


instrumenty = [

    Instrument(),
    Strunowy(),
    Dety(),
    Gitara(),
    Trabka()
]

for instrument in instrumenty:

    print(instrument.graj())