import argparse
import re
from collections import Counter
from pathlib import Path


LOG_LEVEL = re.compile(r"\b(ERROR|WARNING|INFO)\b")


def parse_log_file(log_file: str | Path) -> dict[str, int]:
    """Zlicza poziomy ERROR, WARNING i INFO w pliku z logami."""
    counts: Counter[str] = Counter({"ERROR": 0, "WARNING": 0, "INFO": 0})

    with Path(log_file).open(encoding="utf-8") as file:
        for line in file:
            match = LOG_LEVEL.search(line)
            if match:
                counts[match.group(1)] += 1

    return dict(counts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Zlicza poziomy w pliku logów.")
    parser.add_argument("log_file", help="ścieżka do pliku z logami")
    args = parser.parse_args()

    try:
        print(parse_log_file(args.log_file))
    except OSError as error:
        parser.error(f"nie można odczytać pliku: {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
