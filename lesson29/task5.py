import threading


lista = []
blokada = threading.Lock()
LICZBA_DODAN = 100_000


def dodaj_wartosci(wartosc):
    for _ in range(LICZBA_DODAN):
        with blokada:
            lista.append(wartosc)


def wykonaj_probe(numer_proby):
    global lista
    lista = []

    watek_jedynek = threading.Thread(target=dodaj_wartosci, args=(1,))
    watek_dwojek = threading.Thread(target=dodaj_wartosci, args=(2,))
    watek_jedynek.start()
    watek_dwojek.start()
    watek_jedynek.join()
    watek_dwojek.join()

    print(f"Próba {numer_proby}: długość listy = {len(lista)}")


def main():
    for numer_proby in range(1, 4):
        wykonaj_probe(numer_proby)
    print(f"Oczekiwana długość listy: {2 * LICZBA_DODAN}")


if __name__ == "__main__":
    main()
