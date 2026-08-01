"""Blue-green deployment z dwoma ASG i dokladnie jednym Target Group."""

from __future__ import annotations

import argparse
import base64
import re
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


USER_DATA_TEMPLATE = """#!/bin/bash
set -euo pipefail
install -d -m 0755 /opt/lesson36-app
aws s3 cp "__RELEASE_URI__" /opt/lesson36-app/release.zip
unzip -o /opt/lesson36-app/release.zip -d /opt/lesson36-app
systemctl restart lesson36-app
"""


def require_apply(args: argparse.Namespace) -> None:
    if not args.apply or args.confirm != "BLUE-GREEN-SWITCH":
        raise SystemExit("Wymagane: --apply --confirm BLUE-GREEN-SWITCH")


def numeric_version(value: object) -> str:
    version = str(value)
    if not version.isdecimal() or int(version) < 1:
        raise ValueError("Wersja Launch Template musi byc jawna liczba dodatnia.")
    return version


def build_user_data(release_uri: str) -> str:
    """Buduje user data dla nowej wersji green z artefaktu S3."""
    if not re.fullmatch(r"s3://[A-Za-z0-9.-]+/[A-Za-z0-9._/-]+", release_uri):
        raise ValueError("--release-uri musi być bezpiecznym URI s3://bucket/plik.zip.")
    return USER_DATA_TEMPLATE.replace("__RELEASE_URI__", release_uri)


def get_asg(autoscaling: Any, asg_name: str) -> dict[str, Any]:
    groups = autoscaling.describe_auto_scaling_groups(
        AutoScalingGroupNames=[asg_name]
    ).get("AutoScalingGroups", [])
    if not groups:
        raise ValueError(f"Nie znaleziono ASG: {asg_name}")
    return groups[0]


def in_service_instances(group: dict[str, Any]) -> list[str]:
    return [
        instance["InstanceId"]
        for instance in group.get("Instances", [])
        if instance.get("LifecycleState") == "InService"
    ]


def assert_single_target_group(elbv2: Any, target_group_arn: str) -> None:
    groups = elbv2.describe_target_groups(TargetGroupArns=[target_group_arn]).get(
        "TargetGroups", []
    )
    if len(groups) != 1 or groups[0].get("TargetGroupArn") != target_group_arn:
        raise ValueError("Podany ARN nie identyfikuje jednego Target Group.")


def assert_group_targets(
    group: dict[str, Any], expected: set[str], label: str
) -> None:
    attached = set(group.get("TargetGroupARNs", []))
    if attached != expected:
        raise ValueError(
            f"ASG {label} ma nieoczekiwane Target Groups; deployment wymaga jednego."
        )


def assert_only_target_group_or_none(
    group: dict[str, Any], target_group_arn: str, label: str
) -> None:
    attached = set(group.get("TargetGroupARNs", []))
    if attached - {target_group_arn}:
        raise ValueError(f"ASG {label} ma nieoczekiwany Target Group.")


def template_from_group(
    group: dict[str, Any], expected_template_id: str
) -> tuple[str, str]:
    template = group.get("LaunchTemplate")
    if not template or template.get("LaunchTemplateId") != expected_template_id:
        raise ValueError("Green ASG musi wskazywac podany Launch Template.")
    return expected_template_id, numeric_version(template.get("Version"))


def create_template_version(
    ec2: Any, template_id: str, source_version: str, user_data: str
) -> str:
    response = ec2.create_launch_template_version(
        LaunchTemplateId=template_id,
        SourceVersion=source_version,
        VersionDescription="lesson36-green-release",
        LaunchTemplateData={
            "UserData": base64.b64encode(user_data.encode("utf-8")).decode("ascii")
        },
    )
    return numeric_version(response["LaunchTemplateVersion"]["VersionNumber"])


def start_green_asg(
    autoscaling: Any,
    green: dict[str, Any],
    template_id: str,
    version: str,
    capacity: int,
) -> None:
    if int(green["MaxSize"]) < capacity:
        raise ValueError("Green ASG ma zbyt maly MaxSize.")
    if int(green["DesiredCapacity"]) != 0 or in_service_instances(green):
        raise ValueError("Green ASG musi byc w standby (DesiredCapacity=0) przed deployem.")
    autoscaling.update_auto_scaling_group(
        AutoScalingGroupName=green["AutoScalingGroupName"],
        LaunchTemplate={"LaunchTemplateId": template_id, "Version": version},
        MinSize=capacity,
        DesiredCapacity=capacity,
    )


def wait_for_asg_capacity(
    autoscaling: Any,
    asg_name: str,
    capacity: int,
    timeout_seconds: int,
    poll_seconds: float,
) -> list[str]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        identifiers = in_service_instances(get_asg(autoscaling, asg_name))
        if len(identifiers) >= capacity:
            return identifiers
        time.sleep(poll_seconds)
    raise TimeoutError("Green ASG nie osiagnal wymaganej pojemnosci.")


def health_url_ok(url: str) -> bool:
    request = Request(url, headers={"User-Agent": "lesson36-blue-green"})
    try:
        with urlopen(request, timeout=5) as response:
            return 200 <= response.status < 300
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        return False


def validate_direct_health(urls: list[str], expected_count: int, label: str) -> None:
    """Weryfikuje endpointy instancji przed rejestracja w ALB."""
    if len(urls) < expected_count:
        raise ValueError(f"Podaj health URL dla kazdej instancji {label}.")
    failed = [url for url in urls if not health_url_ok(url)]
    if failed:
        raise RuntimeError(f"Bezposredni health check {label} nie powiodl sie.")


def wait_for_healthy_targets(
    elbv2: Any,
    target_group_arn: str,
    instance_ids: list[str],
    timeout_seconds: int,
    poll_seconds: float,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    targets = [{"Id": identifier} for identifier in instance_ids]
    while time.monotonic() < deadline:
        response = elbv2.describe_target_health(
            TargetGroupArn=target_group_arn, Targets=targets
        )
        states = {
            item["Target"]["Id"]: item.get("TargetHealth", {}).get("State")
            for item in response.get("TargetHealthDescriptions", [])
        }
        if all(states.get(identifier) == "healthy" for identifier in instance_ids):
            return
        time.sleep(poll_seconds)
    raise TimeoutError("Target Group nie potwierdzil zdrowia wszystkich instancji.")


def switch_to_green(
    autoscaling: Any,
    elbv2: Any,
    blue_asg: str,
    green_asg: str,
    target_group_arn: str,
    blue_ids: list[str],
    green_ids: list[str],
    timeout_seconds: int,
    poll_seconds: float,
) -> None:
    """Najpierw rejestruje i sprawdza green, potem odlacza blue."""
    try:
        elbv2.register_targets(
            TargetGroupArn=target_group_arn,
            Targets=[{"Id": identifier} for identifier in green_ids],
        )
        wait_for_healthy_targets(
            elbv2, target_group_arn, green_ids, timeout_seconds, poll_seconds
        )
        autoscaling.attach_load_balancer_target_groups(
            AutoScalingGroupName=green_asg, TargetGroupARNs=[target_group_arn]
        )
        autoscaling.detach_load_balancer_target_groups(
            AutoScalingGroupName=blue_asg, TargetGroupARNs=[target_group_arn]
        )
        elbv2.deregister_targets(
            TargetGroupArn=target_group_arn,
            Targets=[{"Id": identifier} for identifier in blue_ids],
        )
    except Exception as switch_error:
        try:
            restore_blue_after_failed_switch(
                autoscaling,
                elbv2,
                blue_asg,
                green_asg,
                target_group_arn,
                blue_ids,
                green_ids,
                timeout_seconds,
                poll_seconds,
            )
        except Exception as recovery_error:
            raise RuntimeError(
                "Przelaczenie i automatyczne przywrocenie blue nie zostaly potwierdzone."
            ) from recovery_error
        raise RuntimeError(
            "Przelaczenie nie powiodlo sie; potwierdzono przywrocenie ruchu do blue."
        ) from switch_error


def restore_blue_after_failed_switch(
    autoscaling: Any,
    elbv2: Any,
    blue_asg: str,
    green_asg: str,
    target_group_arn: str,
    blue_ids: list[str],
    green_ids: list[str],
    timeout_seconds: int,
    poll_seconds: float,
) -> None:
    """Kompensuje kazdy czesciowy switch, zanim zglosi blad deploymentu."""
    elbv2.register_targets(
        TargetGroupArn=target_group_arn,
        Targets=[{"Id": identifier} for identifier in blue_ids],
    )
    wait_for_healthy_targets(
        elbv2, target_group_arn, blue_ids, timeout_seconds, poll_seconds
    )
    blue = get_asg(autoscaling, blue_asg)
    if target_group_arn not in blue.get("TargetGroupARNs", []):
        autoscaling.attach_load_balancer_target_groups(
            AutoScalingGroupName=blue_asg, TargetGroupARNs=[target_group_arn]
        )
    green = get_asg(autoscaling, green_asg)
    if target_group_arn in green.get("TargetGroupARNs", []):
        autoscaling.detach_load_balancer_target_groups(
            AutoScalingGroupName=green_asg, TargetGroupARNs=[target_group_arn]
        )
    if green_ids:
        elbv2.deregister_targets(
            TargetGroupArn=target_group_arn,
            Targets=[{"Id": identifier} for identifier in green_ids],
        )


def rollback_to_blue(
    autoscaling: Any,
    elbv2: Any,
    args: argparse.Namespace,
    blue_ids: list[str],
    green_ids: list[str],
    blue_attached: bool,
    green_attached: bool,
) -> None:
    """Kodowy rollback utrzymuje green do chwili zdrowej rejestracji blue."""
    validate_direct_health(args.blue_health_url, len(blue_ids), "blue")
    elbv2.register_targets(
        TargetGroupArn=args.target_group_arn,
        Targets=[{"Id": identifier} for identifier in blue_ids],
    )
    wait_for_healthy_targets(
        elbv2,
        args.target_group_arn,
        blue_ids,
        args.timeout_seconds,
        args.poll_seconds,
    )
    if not blue_attached:
        autoscaling.attach_load_balancer_target_groups(
            AutoScalingGroupName=args.blue_asg, TargetGroupARNs=[args.target_group_arn]
        )
    if green_attached:
        autoscaling.detach_load_balancer_target_groups(
            AutoScalingGroupName=args.green_asg, TargetGroupARNs=[args.target_group_arn]
        )
    if green_ids:
        elbv2.deregister_targets(
            TargetGroupArn=args.target_group_arn,
            Targets=[{"Id": identifier} for identifier in green_ids],
        )


def deploy_green(autoscaling: Any, ec2: Any, elbv2: Any, args: argparse.Namespace) -> None:
    assert_single_target_group(elbv2, args.target_group_arn)
    blue = get_asg(autoscaling, args.blue_asg)
    green = get_asg(autoscaling, args.green_asg)
    assert_group_targets(blue, {args.target_group_arn}, "blue")
    assert_group_targets(green, set(), "green")
    blue_ids = in_service_instances(blue)
    if not blue_ids:
        raise RuntimeError("Blue ASG nie ma zadnej instancji InService.")
    template_id, source_version = template_from_group(green, args.launch_template_id)
    user_data = build_user_data(args.release_uri)
    new_version = create_template_version(ec2, template_id, source_version, user_data)
    start_green_asg(
        autoscaling, green, template_id, new_version, args.green_capacity
    )
    green_ids = wait_for_asg_capacity(
        autoscaling,
        args.green_asg,
        args.green_capacity,
        args.timeout_seconds,
        args.poll_seconds,
    )
    validate_direct_health(args.green_health_url, len(green_ids), "green")
    switch_to_green(
        autoscaling,
        elbv2,
        args.blue_asg,
        args.green_asg,
        args.target_group_arn,
        blue_ids,
        green_ids,
        args.timeout_seconds,
        args.poll_seconds,
    )


def perform_rollback(autoscaling: Any, elbv2: Any, args: argparse.Namespace) -> None:
    assert_single_target_group(elbv2, args.target_group_arn)
    blue = get_asg(autoscaling, args.blue_asg)
    green = get_asg(autoscaling, args.green_asg)
    assert_only_target_group_or_none(blue, args.target_group_arn, "blue")
    assert_only_target_group_or_none(green, args.target_group_arn, "green")
    blue_ids = in_service_instances(blue)
    green_ids = in_service_instances(green)
    if not blue_ids:
        raise RuntimeError("Rollback niemozliwy: blue ASG nie ma instancji InService.")
    rollback_to_blue(
        autoscaling,
        elbv2,
        args,
        blue_ids,
        green_ids,
        args.target_group_arn in blue.get("TargetGroupARNs", []),
        args.target_group_arn in green.get("TargetGroupARNs", []),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wdraza blue-green przez jeden Target Group.")
    parser.add_argument("--action", choices=["deploy", "rollback"], required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm")
    parser.add_argument("--region", default="eu-central-1")
    parser.add_argument("--profile")
    parser.add_argument("--blue-asg", required=True)
    parser.add_argument("--green-asg", required=True)
    parser.add_argument("--target-group-arn", required=True)
    parser.add_argument("--launch-template-id")
    parser.add_argument("--release-uri")
    parser.add_argument("--green-capacity", type=int, default=2)
    parser.add_argument("--green-health-url", action="append", default=[])
    parser.add_argument("--blue-health-url", action="append", default=[])
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    args = parser.parse_args()
    if (
        args.green_capacity < 1
        or args.timeout_seconds < 1
        or args.poll_seconds <= 0
        or args.blue_asg == args.green_asg
    ):
        parser.error("Nieprawidlowa pojemnosc, timeout lub nazwy ASG.")
    if args.action == "deploy" and (
        not args.launch_template_id
        or not args.release_uri
        or not args.green_health_url
    ):
        parser.error("Deploy wymaga Launch Template, --release-uri i health URL green.")
    if args.action == "rollback" and not args.blue_health_url:
        parser.error("Rollback wymaga health URL blue.")
    return args


def main() -> None:
    args = parse_args()
    require_apply(args)
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
    except ImportError as error:
        raise SystemExit("Brak bibliotek boto3 i botocore.") from error

    try:
        session = boto3.Session(region_name=args.region, profile_name=args.profile)
        autoscaling = session.client("autoscaling")
        elbv2 = session.client("elbv2")
        if args.action == "deploy":
            deploy_green(autoscaling, session.client("ec2"), elbv2, args)
        else:
            perform_rollback(autoscaling, elbv2, args)
    except NoCredentialsError as error:
        raise SystemExit("Brak konfiguracji AWS credentials lub profilu.") from error
    except (BotoCoreError, ClientError, OSError, RuntimeError, TimeoutError, ValueError) as error:
        raise SystemExit(f"Blue-green nie zostal potwierdzony: {error}") from error
    print("Przelaczenie blue-green zostalo potwierdzone.")


if __name__ == "__main__":
    main()
