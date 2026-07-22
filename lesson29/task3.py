import threading
import time


def pobierz_dane(id_danych):
    time.sleep(2)
    print(f"Pobrano dane o identyfikatorze {id_danych}.")


def main():
    identyfikatory = [1, 2, 3]

    start = time.perf_counter()
    for id_danych in identyfikatory:
        pobierz_dane(id_danych)
    czas_sekwencyjny = time.perf_counter() - start

    start = time.perf_counter()
    watki = []
    for id_danych in identyfikatory:
        watek = threading.Thread(target=pobierz_dane, args=(id_danych,))
        watki.append(watek)
        watek.start()
    for watek in watki:
        watek.join()
    czas_watkow = time.perf_counter() - start

    print(f"Sekwencyjnie: {czas_sekwencyjny:.2f} s")
    print(f"W trzech wątkach: {czas_watkow:.2f} s")
    print("Wersja wątkowa skraca oczekiwanie, ponieważ sleep symuluje operację I/O.")


if __name__ == "__main__":
    main()
