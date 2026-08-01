import argparse
import shutil
from datetime import datetime
from pathlib import Path


def backup_directory(source: Path) -> Path:
    source = source.expanduser().resolve()
    if not source.is_dir():
        raise FileNotFoundError(f"Katalog nie istnieje: {source}")

    backups = (Path.cwd() / "backups").resolve()
    if backups.is_relative_to(source):
        raise ValueError("Katalog backups nie może znajdować się wewnątrz kopiowanego katalogu.")

    backups.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = backups / f"backup_{timestamp}"

    try:
        shutil.copytree(source, target)
    except (OSError, shutil.Error):
        if target.exists():
            shutil.rmtree(target)
        raise
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Tworzy kopię katalogu w backups/.")
    parser.add_argument("source", type=Path, help="katalog do skopiowania")
    args = parser.parse_args()

    try:
        target = backup_directory(args.source)
    except (OSError, ValueError, shutil.Error) as error:
        print(f"Błąd kopii zapasowej: {error}")
        return 1

    print(f"Kopia zapasowa utworzona pomyślnie: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
