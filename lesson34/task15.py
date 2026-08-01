import argparse
import asyncio
import csv
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, PartialCredentialsError
except ImportError:
    boto3 = None

try:
    import requests
except ImportError:
    requests = None


class MonitorError(RuntimeError):
    pass


def add_row(rows: list[dict[str, str]], timestamp: str, kind: str, resource: str, status: str, details: str) -> None:
    rows.append(
        {
            "timestamp": timestamp,
            "type": kind,
            "resource": resource,
            "status": status,
            "details": details,
        }
    )


def collect_instances(ec2, timestamp: str, rows: list[dict[str, str]], alerts: list[str]) -> None:
    for page in ec2.get_paginator("describe_instances").paginate():
        for reservation in page.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                instance_id = instance.get("InstanceId", "unknown")
                state = instance.get("State", {}).get("Name", "unknown")
                details = f"type={instance.get('InstanceType', 'unknown')}; public_ip={instance.get('PublicIpAddress', '-') }"
                add_row(rows, timestamp, "ec2", instance_id, state, details)
                if state != "running":
                    alerts.append(f"EC2 {instance_id} ma stan: {state}")


def ebs_busy_percent(cloudwatch, volume_id: str, now: datetime) -> float | None:
    response = cloudwatch.get_metric_statistics(
        Namespace="AWS/EBS",
        MetricName="VolumeIdleTime",
        Dimensions=[{"Name": "VolumeId", "Value": volume_id}],
        StartTime=now - timedelta(minutes=5),
        EndTime=now,
        Period=300,
        Statistics=["Sum"],
    )
    values = [point["Sum"] for point in response.get("Datapoints", []) if "Sum" in point]
    if not values:
        return None
    idle_seconds = sum(values)
    return round(max(0.0, min(100.0, (1 - idle_seconds / 300) * 100)), 2)


def collect_volumes(ec2, cloudwatch, timestamp: str, rows: list[dict[str, str]], alerts: list[str]) -> None:
    now = datetime.now(timezone.utc)
    for page in ec2.get_paginator("describe_volumes").paginate():
        for volume in page.get("Volumes", []):
            volume_id = volume.get("VolumeId", "unknown")
            state = volume.get("State", "unknown")
            try:
                busy = ebs_busy_percent(cloudwatch, volume_id, now)
                busy_text = "brak danych" if busy is None else f"{busy}%"
            except (ClientError, BotoCoreError) as error:
                busy_text = f"błąd metryki: {error}"
                alerts.append(f"Nie można odczytać metryki EBS {volume_id}")
            attachments = ",".join(item.get("InstanceId", "-") for item in volume.get("Attachments", [])) or "brak"
            details = f"size_gib={volume.get('Size', 0)}; io_busy={busy_text}; instances={attachments}"
            add_row(rows, timestamp, "ebs", volume_id, state, details)
            if state == "error":
                alerts.append(f"EBS {volume_id} ma stan error")


def collect_health(urls: list[str], timestamp: str, rows: list[dict[str, str]], alerts: list[str]) -> None:
    if requests is None:
        raise MonitorError("Brak requests. Zainstaluj pakiet: pip install requests")
    for url in urls:
        started = time.monotonic()
        try:
            response = requests.get(url, timeout=10)
            elapsed_ms = round((time.monotonic() - started) * 1000)
            status = "ok" if response.status_code == 200 else f"http_{response.status_code}"
            add_row(rows, timestamp, "http", url, status, f"response_ms={elapsed_ms}")
            if response.status_code != 200:
                alerts.append(f"Health check {url} zwrócił HTTP {response.status_code}")
        except requests.RequestException as error:
            add_row(rows, timestamp, "http", url, "error", str(error))
            alerts.append(f"Health check {url} nieudany")


def write_csv(csv_path: Path, rows: list[dict[str, str]]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with csv_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["timestamp", "type", "resource", "status", "details"])
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def monitor_once(ec2, cloudwatch, health_urls: list[str], csv_path: Path) -> list[str]:
    timestamp = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, str]] = []
    alerts: list[str] = []
    collect_instances(ec2, timestamp, rows, alerts)
    collect_volumes(ec2, cloudwatch, timestamp, rows, alerts)
    collect_health(health_urls, timestamp, rows, alerts)
    write_csv(csv_path, rows)
    return alerts


async def monitor_loop(ec2, cloudwatch, health_urls: list[str], csv_path: Path, interval: int, once: bool) -> None:
    while True:
        alerts = await asyncio.to_thread(monitor_once, ec2, cloudwatch, health_urls, csv_path)
        for alert in alerts:
            print(f"ALERT: {alert}")
        if once:
            return
        await asyncio.sleep(interval)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor EC2, EBS i HTTP zapisujący metryki do CSV.")
    parser.add_argument("--region", default="eu-central-1")
    parser.add_argument("--health-url", action="append", required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--interval", type=int, default=300, help="Sekundy, domyślnie 300.")
    parser.add_argument("--once", action="store_true", help="Wykonuje jeden pomiar.")
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval musi być dodatni")
    return args


def main() -> int:
    args = parse_args()
    if boto3 is None:
        print("Brak boto3. Zainstaluj pakiet: pip install boto3", file=sys.stderr)
        return 1
    if requests is None:
        print("Brak requests. Zainstaluj pakiet: pip install requests", file=sys.stderr)
        return 1

    try:
        ec2 = boto3.client("ec2", region_name=args.region)
        cloudwatch = boto3.client("cloudwatch", region_name=args.region)
        asyncio.run(monitor_loop(ec2, cloudwatch, args.health_url, args.csv, args.interval, args.once))
    except (NoCredentialsError, PartialCredentialsError):
        print("Brak lub niekompletne poświadczenia AWS", file=sys.stderr)
        return 1
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code", "ClientError")
        print(f"Błąd AWS: {code}", file=sys.stderr)
        return 1
    except BotoCoreError as error:
        print(f"Błąd połączenia z AWS: {error}", file=sys.stderr)
        return 1
    except MonitorError as error:
        print(f"Błąd monitora: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Monitor zatrzymany.")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
