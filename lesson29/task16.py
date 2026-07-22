import argparse
import hashlib
import multiprocessing
from pathlib import Path


def oblicz_sha256(sciezka_tekstem):
    sciezka = Path(sciezka_tekstem)
    try:
        hasher = hashlib.sha256()
        with sciezka.open("rb") as plik:
            for fragment in iter(lambda: plik.read(1024 * 1024), b""):
                hasher.update(fragment)
        return sciezka.name, hasher.hexdigest(), None
    except OSError as blad:
        return sciezka.name, None, str(blad)


def main():
    parser = argparse.ArgumentParser(description="Oblicza SHA256 plików w katalogu.")
    parser.add_argument("katalog", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args()

    if not args.katalog.is_dir():
        parser.error(f"{args.katalog} nie jest katalogiem")

    pliki = [str(plik) for plik in args.katalog.iterdir() if plik.is_file()]
    with multiprocessing.Pool() as pula:
        odpowiedzi = pula.map(oblicz_sha256, pliki)

    hashe = {}
    for nazwa, skrot, blad in odpowiedzi:
        if blad is None:
            hashe[nazwa] = skrot
        else:
            print(f"Nie można odczytać {nazwa}: {blad}")
    print(hashe)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
