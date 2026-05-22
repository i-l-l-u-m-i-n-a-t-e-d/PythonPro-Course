class MetaWalidujMetody(type):

    def __new__(cls, name, bases, dct):
        for nazwa, wartosc in dct.items():

            if nazwa.startswith("__"):
                continue

            if callable(wartosc) and wartosc.__doc__ is None:

                raise TypeError(f"Metoda '{nazwa}' wymaga docstringa.")

        return super().__new__(cls, name, bases, dct)


class PoprawnaKlasa(metaclass=MetaWalidujMetody):

    def metoda_z_docstringiem(self):

        """To jest poprawnie udokumentowana metoda."""
        pass


try:
    class NiepoprawnaKlasa(metaclass=MetaWalidujMetody):

        def metoda_bez_docstringa(self):
            pass

except TypeError as e:
    
    print(e)