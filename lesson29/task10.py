import argparse
import re
import threading
from pathlib import Path


def policz_wystapienia(sciezka, wzorzec, blokada, wynik):
    try:
        tekst = sciezka.read_text(encoding="utf-8", errors="ignore")
    except OSError as blad:
        print(f"Nie można odczytać {sciezka.name}: {blad}")
        return

    liczba = len(wzorzec.findall(tekst))
    with blokada:
        wynik["suma"] += liczba
    print(f"{sciezka.name}: {liczba}")


def main():
    parser = argparse.ArgumentParser(description="Liczy słowo we wszystkich plikach .txt.")
    parser.add_argument("slowo", nargs="?", default="Python", help="szukane słowo")
    parser.add_argument("--katalog", type=Path, default=Path.cwd(), help="katalog z plikami .txt")
    args = parser.parse_args()

    if not args.katalog.is_dir():
        parser.error(f"{args.katalog} nie jest katalogiem")

    wzorzec = re.compile(rf"\b{re.escape(args.slowo)}\b", re.IGNORECASE)
    pliki = [sciezka for sciezka in args.katalog.glob("*.txt") if sciezka.is_file()]
    blokada = threading.Lock()
    wynik = {"suma": 0}
    watki = []

    for sciezka in pliki:
        watek = threading.Thread(target=policz_wystapienia, args=(sciezka, wzorzec, blokada, wynik))
        watki.append(watek)
        watek.start()

    for watek in watki:
        watek.join()

    print(f"Łączna liczba wystąpień słowa \"{args.slowo}\": {wynik['suma']}")


if __name__ == "__main__":
    main()
