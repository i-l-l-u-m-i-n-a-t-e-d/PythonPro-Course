"""Optymalizacja kosztów zasobów AWS dla zadania 18."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def configure_scheduled_scaling(
    autoscaling: Any,
    asg_name: str,
    night_capacity: int,
    day_capacity: int,
    timezone: str = "Europe/Warsaw",
) -> None:
    """Ustawia nocne zmniejszenie i poranne przywrócenie pojemności."""
    autoscaling.put_scheduled_update_group_action(
        AutoScalingGroupName=asg_name,
        ScheduledActionName=f"{asg_name}-night-scale-down",
        Recurrence="0 22 * * *",
        TimeZone=timezone,
        MinSize=night_capacity,
        MaxSize=night_capacity,
        DesiredCapacity=night_capacity,
    )
    autoscaling.put_scheduled_update_group_action(
        AutoScalingGroupName=asg_name,
        ScheduledActionName=f"{asg_name}-morning-scale-up",
        Recurrence="0 7 * * *",
        TimeZone=timezone,
        MinSize=day_capacity,
        MaxSize=day_capacity,
        DesiredCapacity=day_capacity,
    )


def configure_spot_instances(
    autoscaling: Any,
    asg_name: str,
    launch_template_id: str,
    instance_type: str,
) -> None:
    """Konfiguruje Spot tylko dla wskazanej grupy niekrytycznej."""
    autoscaling.update_auto_scaling_group(
        AutoScalingGroupName=asg_name,
        MixedInstancesPolicy={
            "LaunchTemplate": {
                "LaunchTemplateSpecification": {
                    "LaunchTemplateId": launch_template_id,
                    "Version": "$Latest",
                },
                "Overrides": [{"InstanceType": instance_type}],
            },
            "InstancesDistribution": {
                "OnDemandBaseCapacity": 0,
                "OnDemandPercentageAboveBaseCapacity": 0,
                "SpotAllocationStrategy": "price-capacity-optimized",
            },
        },
    )


def configure_release_lifecycle(s3: Any, bucket: str, glacier_after_days: int) -> None:
    """Przenosi bieżące i niebieżące wydania do Glacier."""
    s3.put_bucket_lifecycle_configuration(
        Bucket=bucket,
        LifecycleConfiguration={
            "Rules": [
                {
                    "ID": "archive-old-releases",
                    "Status": "Enabled",
                    "Filter": {"Prefix": "releases/"},
                    "Transitions": [
                        {"Days": glacier_after_days, "StorageClass": "GLACIER"}
                    ],
                    "NoncurrentVersionTransitions": [
                        {"NoncurrentDays": glacier_after_days, "StorageClass": "GLACIER"}
                    ],
                }
            ]
        },
    )


def get_reserved_offering(
    rds: Any,
    db_instance_class: str,
    offering_id: str | None = None,
) -> dict[str, Any]:
    """Pobiera jedno aktualne oferowanie Reserved Instance dla PostgreSQL."""
    if offering_id:
        response = rds.describe_reserved_db_instances_offerings(
            ReservedDBInstancesOfferingId=offering_id
        )
        return response["ReservedDBInstancesOfferings"][0]

    paginator = rds.get_paginator("describe_reserved_db_instances_offerings")
    for page in paginator.paginate(
        DBInstanceClass=db_instance_class,
        ProductDescription="postgresql",
        OfferingType="Partial Upfront",
    ):
        offerings = page.get("ReservedDBInstancesOfferings", [])
        if offerings:
            return offerings[0]
    raise RuntimeError("Nie znaleziono oferty Reserved Instance dla PostgreSQL.")


def estimate_reserved_savings(
    offering: dict[str, Any], on_demand_hourly_rate: float
) -> dict[str, float]:
    """Porównuje koszt oferty RI z kosztem On-Demand w jej okresie."""
    hours = float(offering["Duration"]) / 3600
    on_demand = on_demand_hourly_rate * hours
    reserved = float(offering.get("FixedPrice", 0)) + float(
        offering.get("UsagePrice", 0)
    ) * hours
    savings = on_demand - reserved
    return {
        "hours": hours,
        "on_demand": on_demand,
        "reserved": reserved,
        "savings": savings,
        "savings_percent": 0 if on_demand == 0 else savings / on_demand * 100,
    }


def create_cost_dashboard(cloudwatch: Any, dashboard_name: str) -> None:
    """Tworzy dashboard wykorzystujący metrykę AWS/Billing."""
    body = {
        "widgets": [
            {
                "type": "metric",
                "x": 0,
                "y": 0,
                "width": 12,
                "height": 6,
                "properties": {
                    "title": "Estimated charges",
                    "region": "us-east-1",
                    "view": "timeSeries",
                    "stat": "Maximum",
                    "period": 21600,
                    "metrics": [["AWS/Billing", "EstimatedCharges", "Currency", "USD"]],
                },
            }
        ]
    }
    cloudwatch.put_dashboard(DashboardName=dashboard_name, DashboardBody=json.dumps(body))


def write_report(path: Path, offering: dict[str, Any], estimate: dict[str, float]) -> None:
    """Zapisuje oszacowanie oszczędności bez danych poufnych."""
    lines = [
        "Raport optymalizacji kosztów",
        f"Oferta RI: {offering['ReservedDBInstancesOfferingId']}",
        f"Okres: {estimate['hours']:.0f} godzin",
        f"On-Demand: {estimate['on_demand']:.2f}",
        f"Reserved Instance: {estimate['reserved']:.2f}",
        f"Szacowana oszczędność: {estimate['savings']:.2f}",
        f"Szacowana oszczędność procentowa: {estimate['savings_percent']:.2f}%",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def require_confirmation(value: str | None) -> None:
    if value != "COST-OPTIMIZATION":
        raise SystemExit("Podaj --confirm COST-OPTIMIZATION, aby zmienić zasoby AWS.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Konfiguruje optymalizację kosztów AWS.")
    parser.add_argument("--apply", action="store_true", help="Wykonuje zmiany w AWS.")
    parser.add_argument("--confirm")
    parser.add_argument("--region", default="eu-central-1")
    parser.add_argument("--noncritical-asg", required=True)
    parser.add_argument("--launch-template-id", required=True)
    parser.add_argument("--spot-instance-type", default="t3.micro")
    parser.add_argument("--night-capacity", type=int, default=0)
    parser.add_argument("--day-capacity", type=int, default=2)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--glacier-after-days", type=int, default=30)
    parser.add_argument("--db-instance-class", required=True)
    parser.add_argument("--on-demand-hourly-rate", type=float, required=True)
    parser.add_argument("--offering-id")
    parser.add_argument("--report", type=Path, default=Path("cost-savings-report.txt"))
    parser.add_argument("--dashboard-name", default="lesson36-costs")
    args = parser.parse_args()

    if not args.apply:
        raise SystemExit("To polecenie wymaga jawnej opcji --apply.")
    if args.night_capacity < 0 or args.day_capacity < 0 or args.glacier_after_days < 1:
        raise SystemExit("Pojemności i liczba dni muszą być prawidłowe.")
    require_confirmation(args.confirm)

    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError

        session = boto3.Session(region_name=args.region)
        autoscaling = session.client("autoscaling")
        s3 = session.client("s3")
        rds = session.client("rds")
        billing_cloudwatch = boto3.Session(region_name="us-east-1").client("cloudwatch")
        configure_scheduled_scaling(
            autoscaling, args.noncritical_asg, args.night_capacity, args.day_capacity
        )
        configure_spot_instances(
            autoscaling,
            args.noncritical_asg,
            args.launch_template_id,
            args.spot_instance_type,
        )
        configure_release_lifecycle(s3, args.bucket, args.glacier_after_days)
        offering = get_reserved_offering(rds, args.db_instance_class, args.offering_id)
        estimate = estimate_reserved_savings(offering, args.on_demand_hourly_rate)
        create_cost_dashboard(billing_cloudwatch, args.dashboard_name)
        write_report(args.report, offering, estimate)
    except (BotoCoreError, ClientError) as error:
        raise SystemExit(f"Operacja AWS nie powiodła się: {error}") from error

    print(f"Zapisano raport: {args.report}")


if __name__ == "__main__":
    main()
