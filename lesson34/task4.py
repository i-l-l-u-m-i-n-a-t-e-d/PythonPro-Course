import argparse

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
except ImportError:
    raise SystemExit(
        "Brak boto3. Zainstaluj je: python -m pip install boto3"
    )


def create_s3_bucket(bucket_name: str, region: str) -> bool:
    if not bucket_name or not region:
        raise ValueError("Nazwa bucketa i region są wymagane.")

    s3 = boto3.client("s3", region_name=region)
    parameters = {"Bucket": bucket_name}
    if region != "us-east-1":
        parameters["CreateBucketConfiguration"] = {"LocationConstraint": region}

    try:
        s3.create_bucket(**parameters)
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code", "nieznany błąd")
        if code == "BucketAlreadyExists":
            print(f"Bucket {bucket_name} już istnieje i należy do innego konta.")
            return False
        if code == "BucketAlreadyOwnedByYou":
            print(f"Bucket {bucket_name} już istnieje i należy do Ciebie.")
            return False
        raise

    print(f"Bucket {bucket_name} utworzono w regionie {region}.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Tworzy bucket S3.")
    parser.add_argument("bucket_name", help="unikalna nazwa bucketa")
    parser.add_argument("region", help="np. eu-central-1")
    args = parser.parse_args()

    try:
        return 0 if create_s3_bucket(args.bucket_name, args.region) else 1
    except ValueError as error:
        print(f"Błąd: {error}")
    except NoCredentialsError:
        print("Brak poświadczeń AWS. Skonfiguruj standardowe poświadczenia AWS.")
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code", "nieznany błąd")
        print(f"Nie udało się utworzyć bucketa: {code}")
    except BotoCoreError as error:
        print(f"Nie można połączyć się z AWS: {error.__class__.__name__}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
