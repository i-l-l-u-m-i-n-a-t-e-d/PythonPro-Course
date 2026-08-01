import argparse
import os
import sys

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
except ImportError:
    boto3 = None
    BotoCoreError = ClientError = NoCredentialsError = RuntimeError


def find_group(client, group_name, vpc_id):
    response = client.describe_security_groups(
        Filters=[
            {"Name": "group-name", "Values": [group_name]},
            {"Name": "vpc-id", "Values": [vpc_id]},
        ]
    )
    groups = response.get("SecurityGroups", [])
    return groups[0] if groups else None


def only_web_ingress(group):
    expected_ports = set()
    for rule in group.get("IpPermissions", []):
        port = rule.get("FromPort")
        cidrs = {item.get("CidrIp") for item in rule.get("IpRanges", [])}
        if (
            rule.get("IpProtocol") != "tcp"
            or rule.get("ToPort") != port
            or port not in {80, 443}
            or cidrs != {"0.0.0.0/0"}
            or rule.get("Ipv6Ranges")
            or rule.get("PrefixListIds")
            or rule.get("UserIdGroupPairs")
        ):
            return False
        expected_ports.add(port)
    return expected_ports == {80, 443}


def create_web_security_group(args):
    client = boto3.client("ec2", region_name=args.region)
    existing = find_group(client, args.group_name, args.vpc_id)
    if existing:
        if only_web_ingress(existing):
            print(f"Grupa {existing['GroupId']} już ma wyłącznie reguły HTTP i HTTPS.")
            return
        raise ValueError("Grupa o tej nazwie już istnieje i ma inne reguły wejściowe.")

    response = client.create_security_group(
        GroupName=args.group_name,
        Description="HTTP i HTTPS z Internetu",
        VpcId=args.vpc_id,
    )
    group_id = response["GroupId"]
    try:
        # Brak innych reguł wejściowych blokuje pozostałe porty.
        client.authorize_security_group_ingress(
            GroupId=group_id,
            IpPermissions=[
                {
                    "IpProtocol": "tcp",
                    "FromPort": 80,
                    "ToPort": 80,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                },
                {
                    "IpProtocol": "tcp",
                    "FromPort": 443,
                    "ToPort": 443,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                },
            ],
        )
    except (ClientError, BotoCoreError):
        try:
            client.delete_security_group(GroupId=group_id)
        except (ClientError, BotoCoreError):
            pass
        raise
    print(f"Utworzono Security Group {group_id}.")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Tworzy Security Group dla HTTP i HTTPS.")
    parser.add_argument("--group-name", required=True)
    parser.add_argument("--vpc-id", required=True)
    parser.add_argument(
        "--region",
        default=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"),
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", help="Musi być równe nazwie Security Group.")
    return parser.parse_args()


def main():
    args = parse_arguments()
    if not args.apply:
        print("Podgląd: użyj --apply --confirm <group-name>, aby utworzyć Security Group.")
        return 0
    if args.confirm != args.group_name:
        print("Potwierdzenie nie zgadza się z --group-name.", file=sys.stderr)
        return 2
    if not args.region:
        print("Podaj --region lub ustaw AWS_REGION.", file=sys.stderr)
        return 2
    if boto3 is None:
        print("Brak pakietów boto3 i botocore.", file=sys.stderr)
        return 1
    try:
        create_web_security_group(args)
    except NoCredentialsError:
        print("Brak poświadczeń AWS. Skonfiguruj profil lub rolę IAM.", file=sys.stderr)
        return 1
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    except (ClientError, BotoCoreError) as error:
        print(f"Operacja EC2 nie powiodła się: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
