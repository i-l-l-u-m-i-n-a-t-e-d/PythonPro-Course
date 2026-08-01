import os

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
except ImportError:
    raise SystemExit(
        "Brak boto3. Zainstaluj je: python -m pip install boto3"
    )


def list_ec2_instances() -> None:
    region_name = os.environ.get("AWS_DEFAULT_REGION", "eu-central-1")
    ec2 = boto3.client("ec2", region_name=region_name)
    paginator = ec2.get_paginator("describe_instances")
    found = False

    for page in paginator.paginate():
        for reservation in page.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                found = True
                print(f"ID: {instance.get('InstanceId', 'brak')}")
                print(f"Typ instancji: {instance.get('InstanceType', 'brak')}")
                print(f"Stan: {instance.get('State', {}).get('Name', 'brak')}")
                print(f"Publiczny IP: {instance.get('PublicIpAddress', 'brak')}")
                print()

    if not found:
        print("Brak instancji EC2.")


def main() -> int:
    try:
        list_ec2_instances()
    except NoCredentialsError:
        print("Brak poświadczeń AWS. Skonfiguruj standardowe poświadczenia AWS.")
        return 1
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code", "nieznany błąd")
        print(f"AWS nie udostępnił listy instancji: {code}")
        return 1
    except BotoCoreError as error:
        print(f"Nie można połączyć się z AWS: {error.__class__.__name__}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
