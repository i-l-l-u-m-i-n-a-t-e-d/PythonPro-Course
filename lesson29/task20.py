import multiprocessing
import os
import random
import time
from array import array


def utworz_obraz(wymiar):
    return [array("f", (random.random() for _ in range(wymiar))) for _ in range(wymiar)]


def zastosuj_filtr(obraz):
    suma_pikseli = 0.0
    for wiersz in obraz:
        for piksel in wiersz:
            suma_pikseli += piksel * 1.1
    return suma_pikseli


def main():
    szybki_tryb = os.getenv("LESSON30_FAST") == "1"
    liczba_obrazow = 2 if szybki_tryb else 10
    wymiar = 200 if szybki_tryb else 1000
    obrazy = [utworz_obraz(wymiar) for _ in range(liczba_obrazow)]

    start = time.perf_counter()
    wyniki_sekwencyjne = [zastosuj_filtr(obraz) for obraz in obrazy]
    czas_sekwencyjny = time.perf_counter() - start

    liczba_procesow = min(liczba_obrazow, os.cpu_count() or 1)
    start = time.perf_counter()
    with multiprocessing.Pool(processes=liczba_procesow) as pula:
        wyniki_rownolegle = pula.map(zastosuj_filtr, obrazy)
    czas_rownolegly = time.perf_counter() - start

    print(f"Sekwencyjnie: {czas_sekwencyjny:.2f} s")
    print(f"Równolegle: {czas_rownolegly:.2f} s")
    print(f"Wyniki są zgodne: {wyniki_sekwencyjne == wyniki_rownolegle}")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
