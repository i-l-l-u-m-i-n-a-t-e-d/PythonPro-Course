import multiprocessing
import random


def czy_pierwsza(liczba):
    if liczba < 2:
        return False
    dzielnik = 2
    while dzielnik * dzielnik <= liczba:
        if liczba % dzielnik == 0:
            return False
        dzielnik += 1
    return True


def main():
    random.seed(30)
    liczby = [random.randint(1, 1000) for _ in range(100)]

    with multiprocessing.Pool() as pula:
        wyniki = pula.map(czy_pierwsza, liczby)

    print(f"Znaleziono liczb pierwszych: {sum(wyniki)}")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
