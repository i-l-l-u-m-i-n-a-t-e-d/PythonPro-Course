import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from typing import Any

try:
    import boto3
    from boto3.exceptions import S3UploadFailedError
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, NoRegionError
except ImportError:
    boto3 = None
    S3UploadFailedError = BotoCoreError = ClientError = Exception
    NoCredentialsError = NoRegionError = Exception


def remove_old_backups(
    s3_client: Any, bucket_name: str, prefix: str, retention_days: int = 7
) -> list[str]:
    """Usuwa obiekty backupu starsze niż podana liczba dni."""
    prefix = prefix.strip("/")
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    deleted: list[str] = []
    paginator = s3_client.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=bucket_name, Prefix=f"{prefix}/"):
        for item in page.get("Contents", []):
            modified = item.get("LastModified")
            if modified is None:
                continue
            if modified.tzinfo is None:
                modified = modified.replace(tzinfo=timezone.utc)
            if modified < cutoff:
                key = item["Key"]
                s3_client.delete_object(Bucket=bucket_name, Key=key)
                deleted.append(key)
    return deleted


def backup_directory_to_s3(
    source_directory: str | Path,
    bucket_name: str,
    *,
    prefix: str = "backups",
    retention_days: int = 7,
    s3_client: Any,
) -> tuple[str, list[str]]:
    """Tworzy archiwum katalogu, wysyła je do S3 i wykonuje rotację backupów."""
    source = Path(source_directory)
    if not source.is_dir():
        raise ValueError(f"Katalog źródłowy nie istnieje: {source}")
    if retention_days < 0:
        raise ValueError("retention_days nie może być ujemne")

    prefix = prefix.strip("/")
    if not prefix:
        raise ValueError("prefix backupów nie może być pusty")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    with TemporaryDirectory() as temporary_directory:
        archive_base = Path(temporary_directory) / f"backup_{timestamp}"
        archive = Path(
            shutil.make_archive(
                str(archive_base), "zip", root_dir=source.parent, base_dir=source.name
            )
        )
        key = f"{prefix}/{archive.name}"
        s3_client.upload_file(str(archive), bucket_name, key)

    return key, remove_old_backups(s3_client, bucket_name, prefix, retention_days)


def create_s3_client(region: str | None) -> Any:
    if boto3 is None:
        raise RuntimeError("Brakuje boto3. Zainstaluj je poleceniem: python -m pip install boto3")
    return boto3.client("s3", region_name=region)


def main() -> int:
    parser = argparse.ArgumentParser(description="Wysyła backup katalogu do S3 z rotacją.")
    parser.add_argument("source_directory", help="katalog do zarchiwizowania")
    parser.add_argument("bucket_name", help="docelowy bucket S3")
    parser.add_argument("--prefix", default="backups", help="prefix obiektów backupu")
    parser.add_argument("--retention-days", type=int, default=7)
    parser.add_argument("--region", help="region AWS")
    args = parser.parse_args()

    try:
        key, deleted = backup_directory_to_s3(
            args.source_directory,
            args.bucket_name,
            prefix=args.prefix,
            retention_days=args.retention_days,
            s3_client=create_s3_client(args.region),
        )
    except (ValueError, NoCredentialsError, NoRegionError, ClientError, BotoCoreError, S3UploadFailedError, RuntimeError) as error:
        print(f"Błąd backupu: {error}")
        return 1

    print(f"Backup wysłany: s3://{args.bucket_name}/{key}")
    for old_key in deleted:
        print(f"Usunięto stary backup: {old_key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
