import multiprocessing


def policz_sume_i_srednia(polaczenie):
    try:
        liczby = polaczenie.recv()
        suma = sum(liczby)
        srednia = suma / len(liczby) if liczby else 0
        polaczenie.send((suma, srednia))
    finally:
        polaczenie.close()


def main():
    polaczenie_nadrzedne, polaczenie_potomne = multiprocessing.Pipe()
    proces = multiprocessing.Process(target=policz_sume_i_srednia, args=(polaczenie_potomne,))
    proces.start()
    polaczenie_potomne.close()

    liczby = [2, 4, 6, 8, 10]
    polaczenie_nadrzedne.send(liczby)
    suma, srednia = polaczenie_nadrzedne.recv()
    polaczenie_nadrzedne.close()
    proces.join()

    print(f"Suma: {suma}")
    print(f"Średnia: {srednia}")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
