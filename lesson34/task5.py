import argparse
from pathlib import Path

try:
    import boto3
    from boto3.exceptions import S3UploadFailedError
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
except ImportError:
    raise SystemExit(
        "Brak boto3. Zainstaluj je: python -m pip install boto3"
    )


def upload_jpg_files(directory: Path, bucket_name: str) -> int:
    directory = directory.expanduser()
    if not directory.is_dir():
        raise FileNotFoundError(f"Katalog nie istnieje: {directory}")

    files = sorted(file for file in directory.glob("*.jpg") if file.is_file())
    if not files:
        print("Brak plików .jpg do wysłania.")
        return 0

    s3 = boto3.client("s3")
    for file in files:
        s3.upload_file(str(file), bucket_name, file.name)
        print(f"Wysłano: {file.name}")
    return len(files)


def main() -> int:
    parser = argparse.ArgumentParser(description="Wysyła pliki .jpg do bucketa S3.")
    parser.add_argument("directory", type=Path, help="katalog z plikami .jpg")
    parser.add_argument("bucket_name", help="nazwa docelowego bucketa")
    args = parser.parse_args()

    try:
        uploaded = upload_jpg_files(args.directory, args.bucket_name)
    except FileNotFoundError as error:
        print(f"Błąd: {error}")
        return 1
    except NoCredentialsError:
        print("Brak poświadczeń AWS. Skonfiguruj standardowe poświadczenia AWS.")
        return 1
    except (ClientError, S3UploadFailedError) as error:
        print(f"Nie udało się wysłać pliku: {error.__class__.__name__}")
        return 1
    except (BotoCoreError, OSError) as error:
        print(f"Błąd połączenia lub pliku: {error.__class__.__name__}")
        return 1

    print(f"Wysłano plików: {uploaded}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
