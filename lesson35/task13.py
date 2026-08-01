"""Zero-downtime deployment przez Instance Refresh Auto Scaling Group."""

from __future__ import annotations

import argparse
import base64
import re
import threading
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
    if not args.apply or args.confirm != "ZERO-DOWNTIME-DEPLOYMENT":
        raise SystemExit(
            "Zmiany w AWS wymagaja: --apply --confirm ZERO-DOWNTIME-DEPLOYMENT"
        )


def numeric_version(value: object) -> str:
    """Zwraca jawna, liczbowa wersje Launch Template."""
    version = str(value)
    if not version.isdecimal() or int(version) < 1:
        raise ValueError("ASG musi wskazywac konkretna liczbowa wersje Launch Template.")
    return version


def build_user_data(release_uri: str) -> str:
    """Buduje jawny user data pobierający nowe wydanie z S3."""
    if not re.fullmatch(r"s3://[A-Za-z0-9.-]+/[A-Za-z0-9._/-]+", release_uri):
        raise ValueError("--release-uri musi być bezpiecznym URI s3://bucket/plik.zip.")
    return USER_DATA_TEMPLATE.replace("__RELEASE_URI__", release_uri)


def get_asg(autoscaling: Any, asg_name: str) -> dict[str, Any]:
    groups = autoscaling.describe_auto_scaling_groups(
        AutoScalingGroupNames=[asg_name]
    ).get("AutoScalingGroups", [])
    if not groups:
        raise ValueError(f"Nie znaleziono Auto Scaling Group: {asg_name}")
    return groups[0]


def launch_template_from_asg(
    group: dict[str, Any], expected_template_id: str
) -> tuple[str, str]:
    template = group.get("LaunchTemplate")
    if not template:
        raise ValueError("ASG musi korzystac z Launch Template, nie Launch Configuration.")
    template_id = template.get("LaunchTemplateId")
    if template_id != expected_template_id:
        raise ValueError("Podany Launch Template nie jest konfiguracja wskazanego ASG.")
    return template_id, numeric_version(template.get("Version"))


def configure_elb_health_check(
    elbv2: Any, target_group_arn: str, health_path: str
) -> None:
    """Ustawia health check ALB wymagany przed wymiana instancji."""
    elbv2.modify_target_group(
        TargetGroupArn=target_group_arn,
        HealthCheckEnabled=True,
        HealthCheckProtocol="HTTP",
        HealthCheckPath=health_path,
        HealthCheckIntervalSeconds=30,
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=2,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )


def configure_asg_for_refresh(
    autoscaling: Any,
    group: dict[str, Any],
    target_group_arn: str,
    grace_seconds: int,
) -> None:
    """Zapewnia co najmniej dwie instancje i kontrole zdrowia przez ELB."""
    if int(group["MaxSize"]) < 2:
        raise ValueError("ASG ma MaxSize mniejszy niz wymagane 2 instancje.")
    targets = list(dict.fromkeys([*group.get("TargetGroupARNs", []), target_group_arn]))
    autoscaling.update_auto_scaling_group(
        AutoScalingGroupName=group["AutoScalingGroupName"],
        MinSize=max(2, int(group["MinSize"])),
        DesiredCapacity=max(2, int(group["DesiredCapacity"])),
        HealthCheckType="ELB",
        HealthCheckGracePeriod=grace_seconds,
        TargetGroupARNs=targets,
    )


def application_elb_dimension(arn: str, resource_type: str) -> str:
    try:
        resource = arn.split(":", 5)[5]
    except IndexError as error:
        raise ValueError(f"Nieprawidlowy ARN {resource_type}.") from error
    if not resource.startswith(f"{resource_type}/"):
        raise ValueError(f"ARN nie opisuje zasobu {resource_type}: {arn}")
    # CloudWatch dla ALB oczekuje "app/nazwa/id", bez prefiksu loadbalancer.
    if resource_type == "loadbalancer":
        return resource.removeprefix("loadbalancer/")
    return resource


def create_unhealthy_target_alarm(
    cloudwatch: Any,
    alarm_name: str,
    load_balancer_arn: str,
    target_group_arn: str,
) -> None:
    """Alarm wlaczony do refresh powoduje automatyczny rollback AWS."""
    cloudwatch.put_metric_alarm(
        AlarmName=alarm_name,
        AlarmDescription="Rollback refresh po wykryciu unhealthy targetu ALB",
        ActionsEnabled=True,
        Namespace="AWS/ApplicationELB",
        MetricName="UnHealthyHostCount",
        Dimensions=[
            {
                "Name": "LoadBalancer",
                "Value": application_elb_dimension(load_balancer_arn, "loadbalancer"),
            },
            {
                "Name": "TargetGroup",
                "Value": application_elb_dimension(target_group_arn, "targetgroup"),
            },
        ],
        Statistic="Maximum",
        Period=60,
        EvaluationPeriods=1,
        DatapointsToAlarm=1,
        Threshold=0,
        ComparisonOperator="GreaterThanThreshold",
        TreatMissingData="notBreaching",
    )


def create_launch_template_version(
    ec2: Any, template_id: str, source_version: str, user_data: str
) -> str:
    response = ec2.create_launch_template_version(
        LaunchTemplateId=template_id,
        SourceVersion=source_version,
        VersionDescription="lesson36-zero-downtime",
        LaunchTemplateData={
            "UserData": base64.b64encode(user_data.encode("utf-8")).decode("ascii")
        },
    )
    return numeric_version(response["LaunchTemplateVersion"]["VersionNumber"])


def start_rolling_refresh(
    autoscaling: Any,
    asg_name: str,
    template_id: str,
    version: str,
    alarm_name: str,
    warmup_seconds: int,
) -> str:
    response = autoscaling.start_instance_refresh(
        AutoScalingGroupName=asg_name,
        Strategy="Rolling",
        DesiredConfiguration={
            "LaunchTemplate": {"LaunchTemplateId": template_id, "Version": version}
        },
        Preferences={
            "MinHealthyPercentage": 50,
            "InstanceWarmup": warmup_seconds,
            "AutoRollback": True,
            "AlarmSpecification": {"Alarms": [alarm_name]},
        },
    )
    return response["InstanceRefreshId"]


def is_healthy_http(url: str, timeout: float = 5.0) -> bool:
    request = Request(url, headers={"User-Agent": "lesson36-health-check"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        return False


class AvailabilityMonitor:
    """Mierzy rzeczywiste przerwy za pomoca zapytan HTTP do aplikacji."""

    def __init__(self, health_url: str, interval_seconds: float) -> None:
        self.health_url = health_url
        self.interval_seconds = interval_seconds
        self.failed = threading.Event()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._downtime_started: float | None = None
        self._downtime = 0.0
        self._consecutive_failures = 0
        self._lock = threading.Lock()

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> float:
        self._stop.set()
        self._thread.join(timeout=self.interval_seconds + 6)
        with self._lock:
            if self._downtime_started is not None:
                self._downtime += time.monotonic() - self._downtime_started
                self._downtime_started = None
            return self._downtime

    def _run(self) -> None:
        while not self._stop.is_set():
            now = time.monotonic()
            healthy = is_healthy_http(self.health_url)
            with self._lock:
                if healthy:
                    self._consecutive_failures = 0
                    if self._downtime_started is not None:
                        self._downtime += now - self._downtime_started
                        self._downtime_started = None
                else:
                    self._consecutive_failures += 1
                    if self._downtime_started is None:
                        self._downtime_started = now
                    # Dwa bledy odpowiadaja progowi target group.
                    if self._consecutive_failures >= 2:
                        self.failed.set()
            self._stop.wait(self.interval_seconds)


def wait_for_refresh(
    autoscaling: Any,
    asg_name: str,
    refresh_id: str,
    monitor: AvailabilityMonitor,
    timeout_seconds: int,
    poll_seconds: float,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if monitor.failed.is_set():
            autoscaling.rollback_instance_refresh(AutoScalingGroupName=asg_name)
            wait_for_rollback(
                autoscaling, asg_name, refresh_id, timeout_seconds, poll_seconds
            )
            raise RuntimeError(
                "Health endpoint zawiodl; potwierdzono rollback Instance Refresh."
            )
        response = autoscaling.describe_instance_refreshes(
            AutoScalingGroupName=asg_name, InstanceRefreshIds=[refresh_id]
        )
        refreshes = response.get("InstanceRefreshes", [])
        if not refreshes:
            time.sleep(poll_seconds)
            continue
        status = refreshes[0].get("Status")
        if status == "Successful":
            return
        if status in {"Failed", "Cancelled", "RollbackFailed", "RollbackSuccessful"}:
            reason = refreshes[0].get("StatusReason", "brak szczegolow")
            raise RuntimeError(f"Instance Refresh zakonczyl sie statusem {status}: {reason}")
        time.sleep(poll_seconds)
    raise TimeoutError("Przekroczono czas oczekiwania na Instance Refresh.")


def wait_for_rollback(
    autoscaling: Any,
    asg_name: str,
    refresh_id: str,
    timeout_seconds: int,
    poll_seconds: float,
) -> None:
    """Nie uznaje rollbacku za wykonany, dopoki AWS go nie potwierdzi."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = autoscaling.describe_instance_refreshes(
            AutoScalingGroupName=asg_name, InstanceRefreshIds=[refresh_id]
        )
        refreshes = response.get("InstanceRefreshes", [])
        if not refreshes:
            time.sleep(poll_seconds)
            continue
        status = refreshes[0].get("Status")
        if status == "RollbackSuccessful":
            return
        if status in {"RollbackFailed", "Cancelled"}:
            reason = refreshes[0].get("StatusReason", "brak szczegolow")
            raise RuntimeError(f"Rollback Instance Refresh zakonczyl sie {status}: {reason}")
        time.sleep(poll_seconds)
    raise TimeoutError("Przekroczono czas oczekiwania na potwierdzenie rollbacku.")


def verify_asg_targets(
    autoscaling: Any, elbv2: Any, asg_name: str, target_group_arn: str
) -> None:
    group = get_asg(autoscaling, asg_name)
    instance_ids = [
        instance["InstanceId"]
        for instance in group.get("Instances", [])
        if instance.get("LifecycleState") == "InService"
    ]
    if len(instance_ids) < 2:
        raise RuntimeError("Po refresh nie ma co najmniej dwoch instancji InService.")
    health = elbv2.describe_target_health(TargetGroupArn=target_group_arn)
    states = {
        item["Target"]["Id"]: item.get("TargetHealth", {}).get("State")
        for item in health.get("TargetHealthDescriptions", [])
    }
    unhealthy = [identifier for identifier in instance_ids if states.get(identifier) != "healthy"]
    if unhealthy:
        raise RuntimeError(f"ALB nie potwierdzil zdrowia instancji: {', '.join(unhealthy)}")


def deploy(
    autoscaling: Any,
    ec2: Any,
    elbv2: Any,
    cloudwatch: Any,
    args: argparse.Namespace,
) -> float:
    if not is_healthy_http(args.health_url):
        raise RuntimeError("Health URL nie odpowiada 2xx przed rozpoczeciem deploymentu.")
    group = get_asg(autoscaling, args.auto_scaling_group)
    template_id, source_version = launch_template_from_asg(
        group, args.launch_template_id
    )
    configure_elb_health_check(elbv2, args.target_group_arn, args.health_path)
    configure_asg_for_refresh(
        autoscaling, group, args.target_group_arn, args.grace_seconds
    )
    create_unhealthy_target_alarm(
        cloudwatch,
        args.alarm_name,
        args.load_balancer_arn,
        args.target_group_arn,
    )
    user_data = build_user_data(args.release_uri)
    new_version = create_launch_template_version(
        ec2, template_id, source_version, user_data
    )
    monitor = AvailabilityMonitor(args.health_url, args.probe_seconds)
    monitor.start()
    try:
        refresh_id = start_rolling_refresh(
            autoscaling,
            args.auto_scaling_group,
            template_id,
            new_version,
            args.alarm_name,
            args.warmup_seconds,
        )
        wait_for_refresh(
            autoscaling,
            args.auto_scaling_group,
            refresh_id,
            monitor,
            args.timeout_seconds,
            args.poll_seconds,
        )
        verify_asg_targets(
            autoscaling, elbv2, args.auto_scaling_group, args.target_group_arn
        )
    finally:
        downtime = monitor.stop()
    if monitor.failed.is_set() or downtime > 0:
        raise RuntimeError(f"Zaobserwowany downtime wyniosl {downtime:.2f} s.")
    return downtime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wdraza wersje bez downtime przez ASG.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm")
    parser.add_argument("--region", default="eu-central-1")
    parser.add_argument("--profile")
    parser.add_argument("--auto-scaling-group", required=True)
    parser.add_argument("--launch-template-id", required=True)
    parser.add_argument("--target-group-arn", required=True)
    parser.add_argument("--load-balancer-arn", required=True)
    parser.add_argument("--health-url", required=True)
    parser.add_argument("--release-uri", required=True, help="S3 URI nowego wydania ZIP")
    parser.add_argument("--health-path", default="/health")
    parser.add_argument("--alarm-name", default="lesson36-unhealthy-targets")
    parser.add_argument("--warmup-seconds", type=int, default=120)
    parser.add_argument("--grace-seconds", type=int, default=180)
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument("--probe-seconds", type=float, default=1.0)
    args = parser.parse_args()
    if (
        args.warmup_seconds < 1
        or args.grace_seconds < 1
        or args.timeout_seconds < 1
        or args.poll_seconds <= 0
        or args.probe_seconds <= 0
        or not args.health_path.startswith("/")
    ):
        parser.error("Podaj dodatnie czasy i sciezke health zaczynajaca sie od '/'.")
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
        downtime = deploy(
            session.client("autoscaling"),
            session.client("ec2"),
            session.client("elbv2"),
            session.client("cloudwatch"),
            args,
        )
    except NoCredentialsError as error:
        raise SystemExit("Brak konfiguracji AWS credentials lub profilu.") from error
    except (BotoCoreError, ClientError, OSError, RuntimeError, TimeoutError, ValueError) as error:
        raise SystemExit(f"Deployment nie zostal potwierdzony: {error}") from error
    print(f"Deployment zakonczony. Zmierzony downtime: {downtime:.2f} s")


if __name__ == "__main__":
    main()
