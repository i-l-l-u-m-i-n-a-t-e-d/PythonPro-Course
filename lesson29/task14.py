import argparse
import shutil
import tempfile
import threading
from pathlib import Path


def kopiuj_plik(zrodlo, cel, blokada_wypisywania):
    with blokada_wypisywania:
        print(f"Kopiowanie pliku {zrodlo.name}...")
    try:
        shutil.copy2(zrodlo, cel / zrodlo.name)
    except OSError as blad:
        with blokada_wypisywania:
            print(f"Błąd kopiowania {zrodlo.name}: {blad}")
        return
    with blokada_wypisywania:
        print(f"Ukończono kopiowanie pliku {zrodlo.name}")


def kopiuj_wszystkie_pliki(zrodlo, cel):
    cel.mkdir(parents=True, exist_ok=True)
    blokada_wypisywania = threading.Lock()
    watki = []
    for plik in zrodlo.iterdir():
        if plik.is_file():
            watek = threading.Thread(target=kopiuj_plik, args=(plik, cel, blokada_wypisywania))
            watki.append(watek)
            watek.start()

    for watek in watki:
        watek.join()


def uruchom_pokaz():
    with tempfile.TemporaryDirectory(prefix="task14_") as katalog_tymczasowy:
        katalog = Path(katalog_tymczasowy)
        zrodlo = katalog / "zrodlo"
        cel = katalog / "cel"
        zrodlo.mkdir()
        for nazwa in ("pierwszy.txt", "drugi.txt", "trzeci.txt"):
            (zrodlo / nazwa).write_text("Przykładowa zawartość.\n", encoding="utf-8")
        kopiuj_wszystkie_pliki(zrodlo, cel)
        print(f"Skopiowano {len(list(cel.iterdir()))} pliki w trybie demonstracyjnym.")


def main():
    parser = argparse.ArgumentParser(description="Kopiuje pliki w osobnych wątkach.")
    parser.add_argument("zrodlo", nargs="?", type=Path, help="katalog źródłowy")
    parser.add_argument("cel", nargs="?", type=Path, help="katalog docelowy")
    args = parser.parse_args()

    if args.zrodlo is None and args.cel is None:
        uruchom_pokaz()
        return
    if args.zrodlo is None or args.cel is None:
        parser.error("podaj zarówno katalog źródłowy, jak i docelowy")
    if not args.zrodlo.is_dir():
        parser.error(f"{args.zrodlo} nie jest katalogiem")

    kopiuj_wszystkie_pliki(args.zrodlo, args.cel)


if __name__ == "__main__":
    main()
