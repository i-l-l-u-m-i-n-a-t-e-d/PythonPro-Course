import multiprocessing
import os
import sys
import threading
import time


def intensywne_obliczenia(liczba_iteracji):
    return sum(i * i for i in range(liczba_iteracji))


def oblicz_w_watku(liczba_iteracji, indeks, wyniki):
    wyniki[indeks] = intensywne_obliczenia(liczba_iteracji)


def oblicz_w_procesie(liczba_iteracji, kolejka_wynikow):
    kolejka_wynikow.put(intensywne_obliczenia(liczba_iteracji))


def stan_gil():
    sprawdz = getattr(sys, "_is_gil_enabled", None)
    if callable(sprawdz):
        return "włączony" if sprawdz() else "wyłączony"
    return "nie jest udostępniany przez ten interpreter"


def main():
    liczba_iteracji = 2_000_000 if os.getenv("LESSON30_FAST") == "1" else 20_000_000

    start = time.perf_counter()
    wyniki_sekwencyjne = [intensywne_obliczenia(liczba_iteracji) for _ in range(2)]
    czas_sekwencyjny = time.perf_counter() - start

    wyniki_watkow = [None, None]
    start = time.perf_counter()
    watki = [
        threading.Thread(target=oblicz_w_watku, args=(liczba_iteracji, indeks, wyniki_watkow))
        for indeks in range(2)
    ]
    for watek in watki:
        watek.start()
    for watek in watki:
        watek.join()
    czas_watkow = time.perf_counter() - start

    kontekst = multiprocessing.get_context("spawn")
    kolejka_wynikow = kontekst.Queue()
    start = time.perf_counter()
    procesy = [
        kontekst.Process(target=oblicz_w_procesie, args=(liczba_iteracji, kolejka_wynikow))
        for _ in range(2)
    ]
    for proces in procesy:
        proces.start()
    wyniki_procesow = [kolejka_wynikow.get() for _ in procesy]
    for proces in procesy:
        proces.join()
    czas_procesow = time.perf_counter() - start
    kolejka_wynikow.close()
    kolejka_wynikow.join_thread()

    print(f"Interpreter: {sys.implementation.name} {sys.version.split()[0]}")
    print(f"Stan GIL: {stan_gil()}")
    print(f"Sekwencyjnie: {czas_sekwencyjny:.2f} s")
    print(f"Dwa wątki: {czas_watkow:.2f} s")
    print(f"Dwa procesy: {czas_procesow:.2f} s")
    print(f"Wyniki są zgodne: {wyniki_sekwencyjne == wyniki_watkow == wyniki_procesow}")

 


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
