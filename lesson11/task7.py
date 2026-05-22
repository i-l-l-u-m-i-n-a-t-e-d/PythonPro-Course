class Data:

    def __init__(self, dzien, miesiac, rok):

        self.dzien = dzien
        self.miesiac = miesiac
        self.rok = rok

    @classmethod
    def ze_stringa(cls, tekst):

        dzien, miesiac, rok = tekst.split("-")

        return cls(int(dzien), int(miesiac), int(rok))

    def __repr__(self):
        
        return f"Data(dzien={self.dzien}, miesiac={self.miesiac}, rok={self.rok})"


data = Data.ze_stringa("25-12-2023")
print(data)
print(data.dzien)
print(data.miesiac)
print(data.rok)