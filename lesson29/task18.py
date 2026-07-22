import random
import threading


class KontoBankowe:
    def __init__(self, saldo):
        self.saldo = saldo
        self.blokada = threading.Lock()

    def wplac(self, kwota):
        with self.blokada:
            self.saldo += kwota
            return self.saldo

    def wyplac(self, kwota):
        with self.blokada:
            if self.saldo < kwota:
                return False, self.saldo
            self.saldo -= kwota
            return True, self.saldo


def wykonaj_wplate(konto, kwota):
    saldo = konto.wplac(kwota)
    print(f"Wpłata {kwota} zł, saldo: {saldo} zł")


def wykonaj_wyplate(konto, kwota):
    udalo_sie, saldo = konto.wyplac(kwota)
    if udalo_sie:
        print(f"Wypłata {kwota} zł, saldo: {saldo} zł")
    else:
        print(f"Brak środków na wypłatę {kwota} zł, saldo: {saldo} zł")


def main():
    generator = random.Random(30)
    wplaty = [generator.randint(50, 200) for _ in range(5)]
    wyplaty = [generator.randint(50, 200) for _ in range(5)]
    saldo_poczatkowe = 1000
    konto = KontoBankowe(saldo_poczatkowe)

    watki = []
    for kwota in wplaty:
        watki.append(threading.Thread(target=wykonaj_wplate, args=(konto, kwota)))
    for kwota in wyplaty:
        watki.append(threading.Thread(target=wykonaj_wyplate, args=(konto, kwota)))

    for watek in watki:
        watek.start()
    for watek in watki:
        watek.join()

    oczekiwane_saldo = saldo_poczatkowe + sum(wplaty) - sum(wyplaty)
    print(f"Oczekiwane saldo: {oczekiwane_saldo} zł")
    print(f"Końcowe saldo: {konto.saldo} zł")


if __name__ == "__main__":
    main()
