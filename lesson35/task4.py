import argparse
import os
import shutil
import sys
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

try:
    import boto3
    from boto3.exceptions import S3UploadFailedError
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
except ImportError:
    boto3 = None
    S3UploadFailedError = BotoCoreError = ClientError = NoCredentialsError = RuntimeError


def object_url(bucket, key, region):
    endpoint = "s3.amazonaws.com" if region == "us-east-1" else f"s3.{region}.amazonaws.com"
    return f"https://{bucket}.{endpoint}/{quote(key, safe='/')}"


def upload_application_folder(folder, bucket, key, region):
    archive_base = folder.parent / f".{folder.name}-{uuid4().hex}"
    archive_path = Path(f"{archive_base}.zip")
    try:
        archive_path = Path(
            shutil.make_archive(
                str(archive_base),
                "zip",
                root_dir=folder.parent,
                base_dir=folder.name,
            )
        )
        boto3.client("s3", region_name=region).upload_file(archive_path, bucket, key)
    finally:
        archive_path.unlink(missing_ok=True)
    return object_url(bucket, key, region)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Kompresuje folder i wysyła ZIP do S3.")
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--key")
    parser.add_argument(
        "--region",
        default=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"),
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", help="Musi być równe nazwie bucketu.")
    return parser.parse_args()


def main():
    args = parse_arguments()
    folder = args.folder.resolve()
    if not folder.is_dir():
        print("--folder musi wskazywać istniejący katalog.", file=sys.stderr)
        return 2
    key = args.key or f"{folder.name}.zip"
    if not args.apply:
        print(f"Podgląd: {folder} zostanie wysłany jako s3://{args.bucket}/{key}.")
        return 0
    if args.confirm != args.bucket:
        print("Potwierdzenie nie zgadza się z --bucket.", file=sys.stderr)
        return 2
    if not args.region:
        print("Podaj --region lub ustaw AWS_REGION.", file=sys.stderr)
        return 2
    if boto3 is None:
        print("Brak pakietów boto3 i botocore.", file=sys.stderr)
        return 1
    try:
        url = upload_application_folder(folder, args.bucket, key, args.region)
    except NoCredentialsError:
        print("Brak poświadczeń AWS. Skonfiguruj profil lub rolę IAM.", file=sys.stderr)
        return 1
    except (ClientError, BotoCoreError, S3UploadFailedError, OSError) as error:
        print(f"Upload do S3 nie powiódł się: {error}", file=sys.stderr)
        return 1
    print(f"URL obiektu: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
