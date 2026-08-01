import argparse
import os
import sys
from datetime import datetime, timezone

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, WaiterError
except ImportError:
    boto3 = None
    BotoCoreError = ClientError = NoCredentialsError = WaiterError = RuntimeError


def existing_instance(client, identifier):
    try:
        response = client.describe_db_instances(DBInstanceIdentifier=identifier)
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code")
        if code in {"DBInstanceNotFound", "DBInstanceNotFoundFault"}:
            return None
        raise
    instances = response.get("DBInstances", [])
    return instances[0] if instances else None


def create_instance_and_snapshot(args, password):
    client = boto3.client("rds", region_name=args.region)
    if existing_instance(client, args.db_identifier):
        print(f"Instancja {args.db_identifier} już istnieje; nic nie zmieniono.")
        return

    client.create_db_instance(
        DBInstanceIdentifier=args.db_identifier,
        Engine="postgres",
        DBInstanceClass="db.t3.micro",
        AllocatedStorage=20,
        MasterUsername=args.master_username,
        MasterUserPassword=password,
        DBSubnetGroupName=args.db_subnet_group,
        VpcSecurityGroupIds=args.security_group_ids,
        BackupRetentionPeriod=3,
        PubliclyAccessible=False,
    )
    print("Utworzono instancję RDS, oczekiwanie na status available...")
    client.get_waiter("db_instance_available").wait(
        DBInstanceIdentifier=args.db_identifier,
        WaiterConfig={"Delay": 30, "MaxAttempts": 120},
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    snapshot_id = args.snapshot_identifier or f"{args.db_identifier}-manual-{timestamp}"
    client.create_db_snapshot(
        DBSnapshotIdentifier=snapshot_id,
        DBInstanceIdentifier=args.db_identifier,
    )
    print("Tworzony jest manualny snapshot...")
    client.get_waiter("db_snapshot_available").wait(
        DBSnapshotIdentifier=snapshot_id,
        WaiterConfig={"Delay": 30, "MaxAttempts": 120},
    )
    print(f"Snapshot {snapshot_id} ma status available.")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Tworzy PostgreSQL RDS i manualny snapshot.")
    parser.add_argument("--db-identifier", required=True)
    parser.add_argument("--db-subnet-group", required=True)
    parser.add_argument("--security-group-id", dest="security_group_ids", action="append", required=True)
    parser.add_argument("--master-username", required=True)
    parser.add_argument("--master-password-env", required=True)
    parser.add_argument("--snapshot-identifier")
    parser.add_argument(
        "--region",
        default=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"),
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", help="Musi być równe identyfikatorowi instancji.")
    return parser.parse_args()


def main():
    args = parse_arguments()
    if not args.apply:
        print("Podgląd: użyj --apply --confirm <db-identifier>, aby utworzyć zasoby.")
        return 0
    if args.confirm != args.db_identifier:
        print("Potwierdzenie nie zgadza się z --db-identifier.", file=sys.stderr)
        return 2
    if not args.region:
        print("Podaj --region lub ustaw AWS_REGION.", file=sys.stderr)
        return 2
    if boto3 is None:
        print("Brak pakietów boto3 i botocore.", file=sys.stderr)
        return 1

    password = os.getenv(args.master_password_env)
    if not password:
        print("Brak hasła w wskazanej zmiennej środowiskowej.", file=sys.stderr)
        return 2

    try:
        create_instance_and_snapshot(args, password)
    except NoCredentialsError:
        print("Brak poświadczeń AWS. Skonfiguruj profil lub rolę IAM.", file=sys.stderr)
        return 1
    except (ClientError, BotoCoreError, WaiterError) as error:
        print(f"Operacja RDS nie powiodła się: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
