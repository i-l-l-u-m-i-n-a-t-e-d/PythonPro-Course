import argparse
from typing import Any

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, NoRegionError
except ImportError:
    boto3 = None
    BotoCoreError = ClientError = Exception
    NoCredentialsError = NoRegionError = Exception


def sync_s3_buckets(
    source_bucket: str,
    destination_bucket: str,
    *,
    source_client: Any,
    destination_client: Any,
) -> list[str]:
    """Kopiuje wszystkie obiekty S3 do bucketa w drugim regionie."""
    if source_bucket == destination_bucket:
        raise ValueError("Bucket źródłowy i docelowy muszą być różne")

    copied: list[str] = []
    paginator = source_client.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=source_bucket):
        for item in page.get("Contents", []):
            key = item["Key"]
            destination_client.copy_object(
                Bucket=destination_bucket,
                Key=key,
                CopySource={"Bucket": source_bucket, "Key": key},
            )
            copied.append(key)
    return copied


def create_s3_client(region: str) -> Any:
    if boto3 is None:
        raise RuntimeError("Brakuje boto3. Zainstaluj je poleceniem: python -m pip install boto3")
    return boto3.client("s3", region_name=region)


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronizuje obiekty między bucketami S3.")
    parser.add_argument("source_bucket")
    parser.add_argument("destination_bucket")
    parser.add_argument("--source-region", required=True)
    parser.add_argument("--destination-region", required=True)
    args = parser.parse_args()

    try:
        copied = sync_s3_buckets(
            args.source_bucket,
            args.destination_bucket,
            source_client=create_s3_client(args.source_region),
            destination_client=create_s3_client(args.destination_region),
        )
    except (
        ValueError,
        NoCredentialsError,
        NoRegionError,
        ClientError,
        BotoCoreError,
        RuntimeError,
    ) as error:
        print(f"Błąd synchronizacji: {error}")
        return 1

    print(f"Skopiowano {len(copied)} obiektów.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
