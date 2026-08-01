import argparse
import sys

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, WaiterError
except ImportError:
    boto3 = None
    BotoCoreError = ClientError = NoCredentialsError = WaiterError = RuntimeError


RECORD_NAME = "test.yourdomain.com."
RECORD_VALUE = "1.2.3.4"
RECORD_TTL = 300


def record_belongs_to_zone(record_name, zone_name):
    record_name = record_name.rstrip(".").lower()
    zone_name = zone_name.rstrip(".").lower()
    return record_name == zone_name or record_name.endswith(f".{zone_name}")


def create_record(hosted_zone_id, wait):
    client = boto3.client("route53")
    zone_id = hosted_zone_id.rsplit("/", 1)[-1]
    zone = client.get_hosted_zone(Id=zone_id)["HostedZone"]
    if not record_belongs_to_zone(RECORD_NAME, zone["Name"]):
        raise ValueError("Podana Hosted Zone nie obsługuje test.yourdomain.com.")

    response = client.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            "Changes": [
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": RECORD_NAME,
                        "Type": "A",
                        "TTL": RECORD_TTL,
                        "ResourceRecords": [{"Value": RECORD_VALUE}],
                    },
                }
            ]
        },
    )
    change = response["ChangeInfo"]
    if wait:
        client.get_waiter("resource_record_sets_changed").wait(
            Id=change["Id"],
            WaiterConfig={"Delay": 10, "MaxAttempts": 60},
        )
        print("Zmiana Route 53 ma status INSYNC; propagacja DNS nadal zależy od TTL.")
    else:
        print(f"Zlecono zmianę Route 53 ({change['Id']}, status: {change['Status']}).")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Tworzy rekord A test.yourdomain.com.")
    parser.add_argument("--hosted-zone-id", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", help="Musi być równe test.yourdomain.com.")
    parser.add_argument("--wait", action="store_true", help="Czeka na status INSYNC.")
    return parser.parse_args()


def main():
    args = parse_arguments()
    if not args.apply:
        print("Podgląd: użyj --apply --confirm test.yourdomain.com, aby zmienić DNS.")
        return 0
    if (args.confirm or "").rstrip(".").lower() != RECORD_NAME.rstrip("."):
        print("Potwierdzenie nie zgadza się z nazwą rekordu.", file=sys.stderr)
        return 2
    if boto3 is None:
        print("Brak pakietów boto3 i botocore.", file=sys.stderr)
        return 1
    try:
        create_record(args.hosted_zone_id, args.wait)
    except NoCredentialsError:
        print("Brak poświadczeń AWS. Skonfiguruj profil lub rolę IAM.", file=sys.stderr)
        return 1
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    except (ClientError, BotoCoreError, WaiterError) as error:
        print(f"Operacja Route 53 nie powiodła się: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
