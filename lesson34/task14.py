import argparse
import ipaddress
import json
import re
import sys
from pathlib import Path

try:
    import boto3
    from boto3.exceptions import S3UploadFailedError
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, PartialCredentialsError
except ImportError:
    boto3 = None


CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
}

DASH_WEBSITE_REGIONS = {
    "ap-northeast-1",
    "ap-southeast-1",
    "ap-southeast-2",
    "eu-west-1",
    "sa-east-1",
    "us-east-1",
    "us-gov-west-1",
    "us-west-1",
    "us-west-2",
}


class WebsiteError(RuntimeError):
    pass


def validate_bucket_name(bucket: str) -> None:
    if not 3 <= len(bucket) <= 63 or not re.fullmatch(r"[a-z0-9][a-z0-9.-]*[a-z0-9]", bucket):
        raise WebsiteError("Nazwa bucketa musi być zgodna z DNS i mieć 3-63 znaków")
    if ".." in bucket or any(part.startswith("-") or part.endswith("-") for part in bucket.split(".")):
        raise WebsiteError("Nazwa bucketa ma niepoprawny format")
    try:
        ipaddress.ip_address(bucket)
    except ValueError:
        return
    raise WebsiteError("Nazwa bucketa nie może być adresem IP")


def find_site_files(site_dir: Path, index_document: str) -> list[Path]:
    if not site_dir.is_dir():
        raise WebsiteError(f"Katalog strony nie istnieje: {site_dir}")
    if not (site_dir / index_document).is_file():
        raise WebsiteError(f"Brak dokumentu startowego: {index_document}")
    files = [path for path in site_dir.rglob("*") if path.is_file() and path.suffix.lower() in CONTENT_TYPES]
    if not files:
        raise WebsiteError("Brak plików HTML, CSS lub JS do wysłania")
    return files


def create_bucket(s3, bucket: str, region: str) -> None:
    try:
        if region == "us-east-1":
            s3.create_bucket(Bucket=bucket)
        else:
            s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint": region})
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code", "ClientError")
        if code in {"BucketAlreadyExists", "BucketAlreadyOwnedByYou"}:
            raise WebsiteError(f"Bucket {bucket} już istnieje - wybierz nową nazwę") from error
        raise WebsiteError(f"Nie udało się utworzyć bucketa: {code}") from error


def configure_website(s3, bucket: str, index_document: str, error_document: str | None) -> None:
    configuration = {"IndexDocument": {"Suffix": index_document}}
    if error_document:
        configuration["ErrorDocument"] = {"Key": error_document}

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadWebsiteFiles",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket}/*",
            }
        ],
    }
    try:
        s3.put_public_access_block(
            Bucket=bucket,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": False,
                "IgnorePublicAcls": False,
                "BlockPublicPolicy": False,
                "RestrictPublicBuckets": False,
            },
        )
        s3.put_bucket_website(Bucket=bucket, WebsiteConfiguration=configuration)
        s3.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code", "ClientError")
        raise WebsiteError(f"Nie udało się skonfigurować publicznej strony: {code}") from error


def upload_site(s3, bucket: str, site_dir: Path, files: list[Path]) -> None:
    try:
        for path in files:
            key = path.relative_to(site_dir).as_posix()
            s3.upload_file(str(path), bucket, key, ExtraArgs={"ContentType": CONTENT_TYPES[path.suffix.lower()]})
    except (ClientError, S3UploadFailedError) as error:
        if isinstance(error, ClientError):
            details = error.response.get("Error", {}).get("Code", "ClientError")
        else:
            details = str(error)
        raise WebsiteError(f"Nie udało się wysłać plików: {details}") from error


def website_url(bucket: str, region: str) -> str:
    separator = "-" if region in DASH_WEBSITE_REGIONS else "."
    return f"http://{bucket}.s3-website{separator}{region}.amazonaws.com"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publikuje statyczną stronę HTML/CSS/JS w Amazon S3.")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--site-dir", type=Path, required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--index-document", default="index.html")
    parser.add_argument("--error-document", default="error.html")
    parser.add_argument("--execute", action="store_true", help="Potwierdza utworzenie publicznego bucketa.")
    args = parser.parse_args()
    if not args.execute:
        parser.error("Dodaj --execute, aby utworzyć publiczną stronę")
    return args


def main() -> int:
    args = parse_args()
    if boto3 is None:
        print("Brak boto3. Zainstaluj pakiet: pip install boto3", file=sys.stderr)
        return 1

    try:
        validate_bucket_name(args.bucket)
        files = find_site_files(args.site_dir, args.index_document)
        error_document = args.error_document if (args.site_dir / args.error_document).is_file() else None
        s3 = boto3.client("s3", region_name=args.region)
        create_bucket(s3, args.bucket, args.region)
        configure_website(s3, args.bucket, args.index_document, error_document)
        upload_site(s3, args.bucket, args.site_dir, files)
    except (NoCredentialsError, PartialCredentialsError):
        print("Brak lub niekompletne poświadczenia AWS", file=sys.stderr)
        return 1
    except WebsiteError as error:
        print(f"Błąd wdrożenia strony: {error}", file=sys.stderr)
        return 1
    except BotoCoreError as error:
        print(f"Błąd połączenia z AWS: {error}", file=sys.stderr)
        return 1

    print(f"URL strony: {website_url(args.bucket, args.region)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
