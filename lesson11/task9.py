from dataclasses import dataclass


class BrakSrodkowError(Exception):
    pass


@dataclass
class KontoBankowe:
    _saldo: float

    @property
    def saldo(self):
        return self._saldo

    def wplac(self, kwota):
        if kwota < 0:
            raise ValueError("Kwota wpłaty nie może być ujemna.")
        self._saldo += kwota

    def wyplac(self, kwota):
        if kwota < 0:
            raise ValueError("Kwota wypłaty nie może być ujemna.")

        if kwota > self._saldo:
            raise BrakSrodkowError("Brak środków na koncie.")

        self._saldo -= kwota


konto = KontoBankowe(100)

try:
    konto.wplac(50)
    print(konto.saldo)

    konto.wyplac(30)
    print(konto.saldo)

    konto.wplac(-10)

except ValueError as e:
    print(e)

except BrakSrodkowError as e:
    print(e)


try:
    konto.wyplac(1000)

except ValueError as e:
    print(e)

except BrakSrodkowError as e:
    print(e)
