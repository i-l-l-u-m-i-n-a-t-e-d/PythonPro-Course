import os
import threading
import time


suma_calkowita = 0
blokada = threading.Lock()


def sumuj_fragment(dane, poczatek, koniec):
    global suma_calkowita
    suma_fragmentu = sum(dane[poczatek:koniec])
    with blokada:
        suma_calkowita += suma_fragmentu


def main():
    global suma_calkowita

    liczba_elementow = 1_000_000 if os.getenv("LESSON30_FAST") == "1" else 10_000_000
    dane = [1] * liczba_elementow
    rozmiar_fragmentu = liczba_elementow // 4
    suma_calkowita = 0

    start = time.perf_counter()
    watki = []
    for numer in range(4):
        poczatek = numer * rozmiar_fragmentu
        koniec = liczba_elementow if numer == 3 else poczatek + rozmiar_fragmentu
        watek = threading.Thread(target=sumuj_fragment, args=(dane, poczatek, koniec))
        watki.append(watek)
        watek.start()

    for watek in watki:
        watek.join()

    czas = time.perf_counter() - start
    print(f"Suma całkowita: {suma_calkowita}")
    print(f"Czas wykonania: {czas:.4f} s")


if __name__ == "__main__":
    main()
