import argparse
from datetime import datetime, timezone
from typing import Any

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, NoRegionError
except ImportError:
    boto3 = None
    BotoCoreError = ClientError = Exception
    NoCredentialsError = NoRegionError = Exception


class AWSCostCalculator:
    """Szacuje koszt działających instancji EC2 według uproszczonego cennika."""

    HOURLY_PRICES = {"t3.micro": 0.01, "t3.small": 0.02, "t3.medium": 0.04}

    def __init__(self, ec2_client: Any, prices: dict[str, float] | None = None) -> None:
        self.ec2_client = ec2_client
        self.prices = self.HOURLY_PRICES if prices is None else prices

    def get_instances(self) -> list[dict[str, Any]]:
        instances: list[dict[str, Any]] = []
        paginator = self.ec2_client.get_paginator("describe_instances")
        for page in paginator.paginate():
            for reservation in page.get("Reservations", []):
                instances.extend(reservation.get("Instances", []))
        return instances

    def calculate_costs(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        report: list[dict[str, Any]] = []
        total = 0.0

        for instance in self.get_instances():
            if instance.get("State", {}).get("Name") != "running":
                continue
            instance_type = instance["InstanceType"]
            launch_time = instance.get("LaunchTime")
            if launch_time is None:
                continue
            if launch_time.tzinfo is None:
                launch_time = launch_time.replace(tzinfo=timezone.utc)
            hours = max(0.0, (now - launch_time).total_seconds() / 3600)
            hourly_price = self.prices.get(instance_type)
            cost = None if hourly_price is None else hours * hourly_price
            if cost is not None:
                total += cost
            report.append(
                {
                    "instance_id": instance["InstanceId"],
                    "instance_type": instance_type,
                    "running_hours": round(hours, 2),
                    "hourly_price_usd": hourly_price,
                    "estimated_cost_usd": None if cost is None else round(cost, 2),
                }
            )

        return {"instances": report, "total_estimated_cost_usd": round(total, 2)}


def create_ec2_client(region: str | None) -> Any:
    if boto3 is None:
        raise RuntimeError("Brakuje boto3. Zainstaluj je poleceniem: python -m pip install boto3")
    return boto3.client("ec2", region_name=region)


def main() -> int:
    parser = argparse.ArgumentParser(description="Szacuje koszt działających instancji EC2.")
    parser.add_argument("--region", help="region AWS")
    args = parser.parse_args()

    try:
        report = AWSCostCalculator(create_ec2_client(args.region)).calculate_costs()
    except (NoCredentialsError, NoRegionError, ClientError, BotoCoreError, RuntimeError) as error:
        print(f"Błąd pobierania danych EC2: {error}")
        return 1

    for instance in report["instances"]:
        print(instance)
    print(f"Łączny szacowany koszt: ${report['total_estimated_cost_usd']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
