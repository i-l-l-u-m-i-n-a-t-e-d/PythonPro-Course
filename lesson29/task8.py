import multiprocessing
import os
import sys


def pobierz_imie(kolejka):
   
    if os.name == "nt" and not sys.stdin.isatty():
        try:
            sys.stdin = open("CONIN$", "r", encoding="utf-8")
        except OSError:
            pass
    try:
        imie = input("Podaj swoje imię: ").strip()
    except EOFError:
        imie = ""
    kolejka.put(imie)


def main():
    kolejka_imion = multiprocessing.Queue()
    proces = multiprocessing.Process(target=pobierz_imie, args=(kolejka_imion,))
    proces.start()

    imie = kolejka_imion.get()
    proces.join()
    kolejka_imion.close()
    kolejka_imion.join_thread()

    if imie:
        print(f"Witaj, {imie}!")
    else:
        print("Nie podano imienia.")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
