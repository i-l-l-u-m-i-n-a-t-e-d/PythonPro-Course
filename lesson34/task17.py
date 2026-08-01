import argparse
from io import BytesIO
from pathlib import PurePosixPath
from time import sleep
from typing import Any


IMAGE_SUFFIXES = {".jpg", ".png"}


def create_s3_client():
    try:
        import boto3
    except ImportError as error:
        raise RuntimeError("Zainstaluj boto3, aby połączyć się z S3.") from error
    return boto3.client("s3")


def list_image_keys(s3_client: Any, bucket_name: str):
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket_name):
        for item in page.get("Contents", []):
            key = item.get("Key", "")
            suffix = PurePosixPath(key).suffix.lower()
            if key and not key.startswith("thumbnails/") and suffix in IMAGE_SUFFIXES:
                yield key


def thumbnail_key(source_key: str) -> str:
    parts = [
        part
        for part in PurePosixPath(source_key).parts
        if part not in {"/", ".", ".."}
    ]
    if not parts:
        raise ValueError("Nieprawidłowy klucz obiektu S3.")

    source_path = PurePosixPath(*parts)
    filename = f"{source_path.stem}_thumbnail{source_path.suffix.lower()}"
    return str(PurePosixPath("thumbnails", *source_path.parts[:-1], filename))


def create_thumbnail(image_data: bytes, suffix: str, size: tuple[int, int] = (128, 128)):
    try:
        from PIL import Image
    except ImportError as error:
        raise RuntimeError("Zainstaluj Pillow, aby tworzyć miniatury.") from error

    with Image.open(BytesIO(image_data)) as image:
        image.load()
        image.thumbnail(size)
        output = BytesIO()
        if suffix == ".jpg":
            if image.mode != "RGB":
                image = image.convert("RGB")
            image.save(output, format="JPEG", quality=85)
            return output.getvalue(), "image/jpeg"

        image.save(output, format="PNG")
        return output.getvalue(), "image/png"


def process_new_images(
    bucket_name: str,
    s3_client: Any,
    known_keys: set[str] | None = None,
) -> list[str]:
    known_keys = known_keys if known_keys is not None else set()
    processed = []

    for key in list_image_keys(s3_client, bucket_name):
        if key in known_keys:
            continue

        source = s3_client.get_object(Bucket=bucket_name, Key=key)
        data, content_type = create_thumbnail(
            source["Body"].read(), PurePosixPath(key).suffix.lower()
        )
        s3_client.put_object(
            Bucket=bucket_name,
            Key=thumbnail_key(key),
            Body=data,
            ContentType=content_type,
        )
        known_keys.add(key)
        processed.append(key)

    return processed


def monitor_bucket(
    bucket_name: str,
    s3_client: Any,
    iterations: int = 1,
    interval: float = 60,
) -> None:
    if iterations < 1 or interval < 0:
        raise ValueError("Liczba odczytów musi być dodatnia, a odstęp nieujemny.")

    known_keys: set[str] = set()
    for number in range(iterations):
        for key in process_new_images(bucket_name, s3_client, known_keys):
            print(f"Utworzono miniaturę: {key}")
        if number < iterations - 1:
            sleep(interval)


def main() -> int:
    parser = argparse.ArgumentParser(description="Symulacja S3 Event i Lambda.")
    parser.add_argument("bucket", help="Nazwa monitorowanego bucketa S3")
    parser.add_argument("--iterations", type=int, default=1, help="Liczba odczytów")
    parser.add_argument("--interval", type=float, default=60, help="Odstęp w sekundach")
    args = parser.parse_args()

    try:
        client = create_s3_client()
    except RuntimeError as error:
        print(f"Błąd: {error}")
        return 1

    from botocore.exceptions import BotoCoreError, ClientError

    try:
        monitor_bucket(args.bucket, client, args.iterations, args.interval)
    except (BotoCoreError, ClientError, OSError, RuntimeError, ValueError) as error:
        print(f"Błąd przetwarzania S3: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
