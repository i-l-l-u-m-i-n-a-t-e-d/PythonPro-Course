import os


AWS_VARIABLES = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_DEFAULT_REGION",
)


def read_aws_environment() -> dict[str, bool]:
    """Sprawdza, czy wymagane zmienne AWS są ustawione, bez ujawniania wartości."""
    return {name: bool(os.environ.get(name)) for name in AWS_VARIABLES}


def main() -> int:
    status = read_aws_environment()
    for name, configured in status.items():
        print(f"{name}: {'ustawiona' if configured else 'brak'}")

    missing = [name for name, configured in status.items() if not configured]
    if missing:
        print(f"Ostrzeżenie: brakuje zmiennych: {', '.join(missing)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
