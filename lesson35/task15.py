"""Custom metric ActiveConnections, Step Scaling i test obciazenia Locust."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen


NAMESPACE = "Lesson36/Application"
METRIC_NAME = "ActiveConnections"
PUBLISH_INTERVAL_SECONDS = 60

LOCUSTFILE = """from locust import HttpUser, between, task


class ApplicationUser(HttpUser):
    wait_time = between(0.2, 1.0)

    @task
    def application_request(self):
        self.client.get("/", name="application")

    @task
    def health_check(self):
        self.client.get("/health", name="health")
"""


def metric_dimensions(asg_name: str) -> list[dict[str, str]]:
    return [{"Name": "AutoScalingGroupName", "Value": asg_name}]


def publish_active_connections(cloudwatch: Any, asg_name: str, value: int) -> None:
    """Publikuje liczbe aktywnych polaczen jako metryke Count."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("Liczba aktywnych polaczen musi byc liczba nieujemna.")
    cloudwatch.put_metric_data(
        Namespace=NAMESPACE,
        MetricData=[
            {
                "MetricName": METRIC_NAME,
                "Dimensions": metric_dimensions(asg_name),
                "Timestamp": datetime.now(timezone.utc),
                "Value": value,
                "Unit": "Count",
            }
        ],
    )


def read_active_connections(metric_url: str) -> int:
    request = Request(metric_url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=5) as response:
        if not 200 <= response.status < 300:
            raise RuntimeError(f"Endpoint metryki zwrocil HTTP {response.status}.")
        payload = json.loads(response.read().decode("utf-8"))
    value = payload.get("active_connections")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("Endpoint musi zwracac JSON z active_connections >= 0.")
    return value


def publish_every_minute(
    cloudwatch: Any, asg_name: str, metric_url: str, iterations: int | None
) -> None:
    """Pobiera wartosc aplikacji i wysyla ja nie czesciej niz co 60 sekund."""
    sent = 0
    while iterations is None or sent < iterations:
        started = time.monotonic()
        value = read_active_connections(metric_url)
        publish_active_connections(cloudwatch, asg_name, value)
        sent += 1
        print(f"Opublikowano {METRIC_NAME}={value} ({sent}).")
        if iterations is not None and sent >= iterations:
            return
        time.sleep(max(0.0, PUBLISH_INTERVAL_SECONDS - (time.monotonic() - started)))


def configure_step_scaling(
    autoscaling: Any, cloudwatch: Any, asg_name: str
) -> tuple[str, str]:
    """Tworzy polityki krokowe i alarmy dla progow >100 oraz <20."""
    scale_out = autoscaling.put_scaling_policy(
        AutoScalingGroupName=asg_name,
        PolicyName=f"{asg_name}-active-connections-out",
        PolicyType="StepScaling",
        AdjustmentType="ChangeInCapacity",
        MetricAggregationType="Average",
        Cooldown=60,
        StepAdjustments=[{"MetricIntervalLowerBound": 0.0, "ScalingAdjustment": 1}],
    )
    scale_in = autoscaling.put_scaling_policy(
        AutoScalingGroupName=asg_name,
        PolicyName=f"{asg_name}-active-connections-in",
        PolicyType="StepScaling",
        AdjustmentType="ChangeInCapacity",
        MetricAggregationType="Average",
        Cooldown=60,
        StepAdjustments=[{"MetricIntervalUpperBound": 0.0, "ScalingAdjustment": -1}],
    )
    common = {
        "Namespace": NAMESPACE,
        "MetricName": METRIC_NAME,
        "Dimensions": metric_dimensions(asg_name),
        "Statistic": "Average",
        "Period": PUBLISH_INTERVAL_SECONDS,
        "EvaluationPeriods": 1,
        "DatapointsToAlarm": 1,
        "TreatMissingData": "notBreaching",
    }
    cloudwatch.put_metric_alarm(
        AlarmName=f"{asg_name}-active-connections-over-100",
        AlarmDescription="Scale out gdy ActiveConnections > 100",
        ComparisonOperator="GreaterThanThreshold",
        Threshold=100.0,
        AlarmActions=[scale_out["PolicyARN"]],
        **common,
    )
    cloudwatch.put_metric_alarm(
        AlarmName=f"{asg_name}-active-connections-under-20",
        AlarmDescription="Scale in gdy ActiveConnections < 20",
        ComparisonOperator="LessThanThreshold",
        Threshold=20.0,
        AlarmActions=[scale_in["PolicyARN"]],
        **common,
    )
    return scale_out["PolicyARN"], scale_in["PolicyARN"]


def write_locustfile(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(LOCUSTFILE, encoding="utf-8")


def valid_http_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Adres testu musi zaczynac sie od http:// albo https://.")
    return value


def run_locust(
    locustfile: Path,
    target_url: str,
    users: int,
    spawn_rate: float,
    run_time: str,
    timeout_seconds: int,
) -> None:
    if not locustfile.is_file():
        raise FileNotFoundError(f"Brak pliku Locust: {locustfile}")
    if users < 1 or spawn_rate <= 0 or timeout_seconds < 1:
        raise ValueError("Parametry Locust musza byc dodatnie.")
    executable = shutil.which("locust")
    if not executable:
        raise RuntimeError("Nie znaleziono locust w PATH. Zainstaluj go poza katalogiem oddania.")
    result = subprocess.run(
        [
            executable,
            "--headless",
            "--only-summary",
            "-f",
            str(locustfile),
            "--host",
            valid_http_url(target_url),
            "--users",
            str(users),
            "--spawn-rate",
            str(spawn_rate),
            "--run-time",
            run_time,
        ],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Locust zakonczyl sie bledem: {result.stderr[-500:]}")


def require_aws_confirmation(args: argparse.Namespace) -> None:
    if not args.apply or args.confirm != "ACTIVE-CONNECTIONS":
        raise SystemExit("Zmiany AWS wymagaja: --apply --confirm ACTIVE-CONNECTIONS")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Konfiguruje ActiveConnections i Locust.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm")
    parser.add_argument("--region", default="eu-central-1")
    parser.add_argument("--profile")
    parser.add_argument("--auto-scaling-group")
    parser.add_argument("--configure-scaling", action="store_true")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--metric-url")
    parser.add_argument("--iterations", type=int)
    parser.add_argument("--generate-locustfile", type=Path)
    parser.add_argument("--run-load-test", action="store_true")
    parser.add_argument("--load-test-confirm")
    parser.add_argument("--locustfile", type=Path)
    parser.add_argument("--load-url")
    parser.add_argument("--users", type=int, default=50)
    parser.add_argument("--spawn-rate", type=float, default=5.0)
    parser.add_argument("--run-time", default="2m")
    parser.add_argument("--load-test-timeout-seconds", type=int, default=300)
    args = parser.parse_args()
    if not any(
        [
            args.configure_scaling,
            args.publish,
            args.generate_locustfile,
            args.run_load_test,
        ]
    ):
        parser.error("Wybierz co najmniej jedna operacje.")
    if (args.configure_scaling or args.publish) and not args.auto_scaling_group:
        parser.error("Konfiguracja i publikacja wymagaja --auto-scaling-group.")
    if args.publish and not args.metric_url:
        parser.error("Publikacja wymaga --metric-url.")
    if args.iterations is not None and args.iterations < 1:
        parser.error("--iterations musi byc dodatnie.")
    if args.run_load_test:
        standalone_confirmation = not (
            args.configure_scaling or args.publish
        ) and args.confirm == "LOAD-TEST"
        if args.load_test_confirm != "LOAD-TEST" and not standalone_confirmation:
            parser.error(
                "Uruchomienie obciazenia wymaga --load-test-confirm LOAD-TEST."
            )
        if not args.locustfile or not args.load_url:
            parser.error("Locust wymaga --locustfile i --load-url.")
    return args


def main() -> None:
    args = parse_args()
    if args.configure_scaling or args.publish:
        require_aws_confirmation(args)
        try:
            import boto3
            from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
        except ImportError as error:
            raise SystemExit("Brak bibliotek boto3 i botocore.") from error

        try:
            session = boto3.Session(region_name=args.region, profile_name=args.profile)
            autoscaling = session.client("autoscaling")
            cloudwatch = session.client("cloudwatch")
            if args.configure_scaling:
                configure_step_scaling(autoscaling, cloudwatch, args.auto_scaling_group)
            if args.publish:
                publish_every_minute(
                    cloudwatch,
                    args.auto_scaling_group,
                    args.metric_url,
                    args.iterations,
                )
        except NoCredentialsError as error:
            raise SystemExit("Brak konfiguracji AWS credentials lub profilu.") from error
        except (BotoCoreError, ClientError, OSError, RuntimeError, ValueError) as error:
            raise SystemExit(f"Operacja metryk nie zostala potwierdzona: {error}") from error
    if args.generate_locustfile:
        write_locustfile(args.generate_locustfile)
        print(f"Utworzono plik Locust: {args.generate_locustfile}")
    if args.run_load_test:
        try:
            run_locust(
                args.locustfile,
                args.load_url,
                args.users,
                args.spawn_rate,
                args.run_time,
                args.load_test_timeout_seconds,
            )
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
            raise SystemExit(f"Test Locust nie zostal potwierdzony: {error}") from error
        print("Test Locust zakonczyl sie powodzeniem.")


if __name__ == "__main__":
    main()
