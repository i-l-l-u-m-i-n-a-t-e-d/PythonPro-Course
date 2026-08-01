import os

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
except ImportError:
    raise SystemExit(
        "Brak boto3. Zainstaluj je: python -m pip install boto3"
    )


def list_regions() -> None:
    region_name = os.environ.get("AWS_DEFAULT_REGION", "eu-central-1")
    ec2 = boto3.client("ec2", region_name=region_name)
    response = ec2.describe_regions(AllRegions=True)
    regions = response.get("Regions", [])

    if not regions:
        print("Brak dostępnych regionów EC2.")
        return

    for region in sorted(regions, key=lambda item: item.get("RegionName", "")):
        print(f"{region.get('RegionName', 'brak nazwy')}: {region.get('Endpoint', 'brak endpointu')}")


def main() -> int:
    try:
        list_regions()
    except NoCredentialsError:
        print("Brak poświadczeń AWS. Skonfiguruj standardowe poświadczenia AWS.")
        return 1
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code", "nieznany błąd")
        print(f"AWS nie udostępnił listy regionów: {code}")
        return 1
    except BotoCoreError as error:
        print(f"Nie można połączyć się z AWS: {error.__class__.__name__}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
