"""Kompletny Application Load Balancer z rzetelnym testem z logów ALB."""

from __future__ import annotations

import argparse
import gzip
import io
import re
import shlex
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

try:
    from botocore.exceptions import (
        BotoCoreError,
        ClientError,
        NoCredentialsError,
        PartialCredentialsError,
        WaiterError,
    )
except ImportError:
    class BotoCoreError(Exception):
        pass

    class ClientError(Exception):
        pass

    class NoCredentialsError(Exception):
        pass

    class PartialCredentialsError(Exception):
        pass

    class WaiterError(Exception):
        pass


NAME_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,30}[A-Za-z0-9])?$")


def make_clients(region: str | None, profile: str | None) -> tuple[Any, Any, Any]:
    try:
        import boto3
    except ImportError as error:
        raise RuntimeError("Brakuje boto3. Zainstaluj je w używanym środowisku.") from error

    session = boto3.Session(region_name=region, profile_name=profile)
    return session.client("elbv2"), session.client("ec2"), session.client("s3")


def validate_name(name: str, option: str) -> str:
    if not NAME_PATTERN.fullmatch(name) or len(name) > 32:
        raise ValueError(f"{option} musi mieć 1-32 znaki alfanumeryczne lub '-'.")
    return name


def normalize_log_prefix(prefix: str) -> str:
    normalized = prefix.strip().strip("/")
    if not normalized:
        raise ValueError("--access-log-prefix nie może być pusty.")
    return normalized


def error_code(error: ClientError) -> str:
    return error.response.get("Error", {}).get("Code", "")


def find_load_balancer(client: Any, name: str) -> dict[str, Any] | None:
    try:
        return client.describe_load_balancers(Names=[name])["LoadBalancers"][0]
    except ClientError as error:
        if error_code(error) == "LoadBalancerNotFound":
            return None
        raise


def ensure_load_balancer(
    client: Any,
    name: str,
    subnet_ids: list[str],
    security_group_ids: list[str],
) -> dict[str, Any]:
    load_balancer = find_load_balancer(client, name)
    if load_balancer is None:
        response = client.create_load_balancer(
            Name=name,
            Subnets=subnet_ids,
            SecurityGroups=security_group_ids,
            Scheme="internet-facing",
            Type="application",
            IpAddressType="ipv4",
        )
        return response["LoadBalancers"][0]

    attached_subnets = {zone.get("SubnetId") for zone in load_balancer.get("AvailabilityZones", [])}
    attached_groups = set(load_balancer.get("SecurityGroups", []))
    if load_balancer.get("Type") != "application" or not set(subnet_ids).issubset(attached_subnets):
        raise RuntimeError("Istniejący load balancer nie odpowiada wymaganym dwóm subnetom ALB.")
    if not set(security_group_ids).issubset(attached_groups):
        raise RuntimeError("Istniejący ALB nie ma podanej grupy bezpieczeństwa.")
    return load_balancer


def ensure_target_group(
    client: Any,
    name: str,
    vpc_id: str,
    target_port: int,
    health_path: str,
) -> dict[str, Any]:
    try:
        target_group = client.describe_target_groups(Names=[name])["TargetGroups"][0]
    except ClientError as error:
        if error_code(error) != "TargetGroupNotFound":
            raise
        response = client.create_target_group(
            Name=name,
            Protocol="HTTP",
            Port=target_port,
            VpcId=vpc_id,
            TargetType="instance",
            HealthCheckEnabled=True,
            HealthCheckProtocol="HTTP",
            HealthCheckPath=health_path,
            HealthCheckPort="traffic-port",
            HealthCheckIntervalSeconds=30,
            HealthCheckTimeoutSeconds=5,
            HealthyThresholdCount=2,
            UnhealthyThresholdCount=2,
            Matcher={"HttpCode": "200"},
        )
        return response["TargetGroups"][0]

    required = {
        "Protocol": "HTTP",
        "Port": target_port,
        "HealthCheckPath": health_path,
        "HealthCheckIntervalSeconds": 30,
    }
    if target_group.get("VpcId") != vpc_id or any(
        target_group.get(key) != value for key, value in required.items()
    ):
        raise RuntimeError("Istniejący Target Group ma inne parametry niż wymagane.")
    return target_group


def action_for_target_group(actions: list[dict[str, Any]], target_group_arn: str) -> bool:
    for action in actions:
        if action.get("Type") != "forward":
            continue
        if action.get("TargetGroupArn") == target_group_arn:
            return True
        groups = action.get("ForwardConfig", {}).get("TargetGroups", [])
        if any(group.get("TargetGroupArn") == target_group_arn for group in groups):
            return True
    return False


def ensure_listener(client: Any, load_balancer_arn: str, target_group_arn: str) -> dict[str, Any]:
    listeners = client.describe_listeners(LoadBalancerArn=load_balancer_arn).get("Listeners", [])
    listener = next((item for item in listeners if item.get("Port") == 80 and item.get("Protocol") == "HTTP"), None)
    if listener is not None:
        if not action_for_target_group(listener.get("DefaultActions", []), target_group_arn):
            raise RuntimeError("Istniejący listener HTTP:80 kieruje ruch do innego Target Group.")
        return listener
    response = client.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
    )
    return response["Listeners"][0]


def configure_access_logs(client: Any, load_balancer_arn: str, bucket: str, prefix: str) -> None:
    """Włącza udokumentowane logi ALB do istniejącego bucketu S3."""
    client.modify_load_balancer_attributes(
        LoadBalancerArn=load_balancer_arn,
        Attributes=[
            {"Key": "access_logs.s3.enabled", "Value": "true"},
            {"Key": "access_logs.s3.bucket", "Value": bucket},
            {"Key": "access_logs.s3.prefix", "Value": prefix},
        ],
    )


def wait_for_healthy_targets(
    client: Any,
    target_group_arn: str,
    instance_ids: list[str],
    target_port: int,
    timeout: int,
    interval: int,
) -> None:
    targets = [{"Id": identifier, "Port": target_port} for identifier in instance_ids]
    deadline = time.monotonic() + timeout
    last_states: dict[str, str] = {}
    while time.monotonic() < deadline:
        response = client.describe_target_health(TargetGroupArn=target_group_arn, Targets=targets)
        descriptions = response.get("TargetHealthDescriptions", [])
        last_states = {
            item.get("Target", {}).get("Id", "?"): item.get("TargetHealth", {}).get("State", "unknown")
            for item in descriptions
        }
        if all(last_states.get(identifier) == "healthy" for identifier in instance_ids):
            return
        time.sleep(interval)
    raise RuntimeError(f"Targety nie są healthy przed timeout: {last_states}")


def instance_private_ips(ec2: Any, instance_ids: list[str]) -> dict[str, str]:
    """Mapuje prywatne IP targetów na ich ID, bez wymagań wobec aplikacji HTTP."""
    response = ec2.describe_instances(InstanceIds=instance_ids)
    result: dict[str, str] = {}
    for reservation in response.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            identifier = instance.get("InstanceId")
            private_ip = instance.get("PrivateIpAddress")
            if identifier in instance_ids and private_ip:
                result[private_ip] = identifier
    if set(result.values()) != set(instance_ids):
        raise RuntimeError("Nie udało się odczytać prywatnych IP obu instancji EC2.")
    return result


def probe_url(dns_name: str, path: str, token: str, number: int) -> str:
    separator = "&" if "?" in path else "?"
    return f"http://{dns_name}{path}{separator}alb_probe={token}-{number}"


def send_probe_requests(dns_name: str, path: str, token: str, requests_count: int, timeout: int) -> None:
    """Wysyła kontrolowane HTTP bez polegania na odpowiedzi identyfikującej backend."""
    failures: list[str] = []
    for number in range(1, requests_count + 1):
        try:
            request = urllib.request.Request(
                probe_url(dns_name, path, token, number),
                headers={"Connection": "close", "Cache-Control": "no-cache"},
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if not 200 <= response.status < 400:
                    raise RuntimeError(f"HTTP {response.status}")
                response.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, RuntimeError) as error:
            failures.append(str(error))
    if failures:
        raise RuntimeError(f"Nieudane żądania testowe: {len(failures)}/{requests_count}.")


def access_log_key_prefix(prefix: str) -> str:
    return f"{normalize_log_prefix(prefix)}/AWSLogs/"


def target_host_from_log_value(value: str) -> str | None:
    if not value or value == "-":
        return None
    host, separator, _port = value.rpartition(":")
    if not separator:
        return None
    return host.strip("[]")


def probe_number_from_line(line: str, token: str) -> int | None:
    match = re.search(rf"(?:[?&])alb_probe={re.escape(token)}-(\d+)(?:[&\s\"']|$)", line)
    return int(match.group(1)) if match else None


def logged_probe_targets(
    s3: Any,
    bucket: str,
    prefix: str,
    token: str,
    not_before: datetime,
) -> dict[int, str]:
    """Odczytuje target:port z udokumentowanego pola piątego logu ALB."""
    records: dict[int, str] = {}
    paginator = s3.get_paginator("list_objects_v2")
    minimum_modified = not_before - timedelta(minutes=10)
    for page in paginator.paginate(Bucket=bucket, Prefix=access_log_key_prefix(prefix)):
        for item in page.get("Contents", []):
            key = item.get("Key", "")
            modified = item.get("LastModified")
            if not key.endswith(".log.gz") or (modified and modified < minimum_modified):
                continue
            body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
            try:
                text = gzip.GzipFile(fileobj=io.BytesIO(body)).read().decode("utf-8")
            except (OSError, UnicodeDecodeError) as error:
                raise RuntimeError(f"Nie można odczytać logu ALB {key}: {error}") from error
            for line in text.splitlines():
                number = probe_number_from_line(line, token)
                if number is None:
                    continue
                fields = shlex.split(line)
                if len(fields) < 5:
                    raise RuntimeError("Nieprawidłowy format wiersza logu ALB.")
                target_host = target_host_from_log_value(fields[4])
                if target_host is None:
                    raise RuntimeError("Żądanie testowe nie dotarło do targetu według logu ALB.")
                previous = records.get(number)
                if previous is not None and previous != target_host:
                    raise RuntimeError("Ten sam probe ma sprzeczne targety w logach ALB.")
                records[number] = target_host
    return records


def wait_for_logged_distribution(
    s3: Any,
    *,
    bucket: str,
    prefix: str,
    token: str,
    started_at: datetime,
    request_count: int,
    poll_interval: int,
    timeout: int,
) -> dict[int, str]:
    deadline = time.monotonic() + timeout
    expected_numbers = set(range(1, request_count + 1))
    while time.monotonic() < deadline:
        records = logged_probe_targets(s3, bucket, prefix, token, started_at)
        if set(records) == expected_numbers:
            return records
        time.sleep(poll_interval)
    raise RuntimeError("Nie otrzymano wszystkich logów ALB przed timeout; sprawdź bucket policy i access logs.")


def test_distribution(
    dns_name: str,
    expected_instance_ids: list[str],
    *,
    ec2: Any,
    s3: Any,
    access_log_bucket: str,
    access_log_prefix: str,
    path: str = "/",
    requests_count: int = 40,
    request_timeout: int = 10,
    access_log_timeout: int = 900,
    access_log_poll_interval: int = 30,
) -> dict[str, Any]:
    """Liczy faktyczne targety z logów ALB, a nie z niestandardowego nagłówka aplikacji."""
    ip_to_instance = instance_private_ips(ec2, expected_instance_ids)
    token = uuid.uuid4().hex
    started_at = datetime.now(timezone.utc)
    send_probe_requests(dns_name, path, token, requests_count, request_timeout)
    target_records = wait_for_logged_distribution(
        s3,
        bucket=access_log_bucket,
        prefix=access_log_prefix,
        token=token,
        started_at=started_at,
        request_count=requests_count,
        poll_interval=access_log_poll_interval,
        timeout=access_log_timeout,
    )
    counts = {identifier: 0 for identifier in expected_instance_ids}
    for target_host in target_records.values():
        identifier = ip_to_instance.get(target_host)
        if identifier is None:
            raise RuntimeError(f"Log ALB wskazuje target spoza dwóch instancji: {target_host}")
        counts[identifier] += 1
    if any(count == 0 for count in counts.values()):
        raise RuntimeError("Nie każdy z dwóch targetów obsłużył żądanie testowe.")
    shares = {identifier: round(count * 100 / requests_count, 1) for identifier, count in counts.items()}
    balanced = all(30.0 <= share <= 70.0 for share in shares.values())
    return {
        "requests": requests_count,
        "counts": counts,
        "shares_percent": shares,
        "balanced": balanced,
        "verification": "ALB access logs",
    }


def require_confirmation(args: argparse.Namespace) -> None:
    if not (args.apply and args.confirm):
        raise RuntimeError("Setup ALB wymaga jednocześnie --apply --confirm.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ALB w dwóch subnetach z dwoma instancjami EC2")
    parser.add_argument("--action", choices=("setup", "test"), required=True)
    parser.add_argument("--region", help="Region AWS lub konfiguracja domyślna profilu")
    parser.add_argument("--profile", help="Opcjonalny profil AWS")
    parser.add_argument("--name", default="lesson36-alb")
    parser.add_argument("--target-group-name", default="lesson36-alb-tg")
    parser.add_argument("--vpc-id", help="Wymagane dla setup")
    parser.add_argument("--subnet-id", action="append", default=[], help="Podaj dokładnie dwie różne subnety")
    parser.add_argument("--security-group-id", action="append", default=[])
    parser.add_argument("--instance-id", action="append", default=[], help="Podaj dokładnie dwie instancje EC2")
    parser.add_argument("--target-port", type=int, default=8000)
    parser.add_argument("--health-path", default="/health")
    parser.add_argument("--dns-name", help="DNS ALB dla --action test")
    parser.add_argument("--expected-instance-id", action="append", default=[])
    parser.add_argument("--access-log-bucket", help="Istniejący bucket S3 z polityką dla logów ALB")
    parser.add_argument("--access-log-prefix", default="lesson36-alb-logs")
    parser.add_argument("--path", default="/")
    parser.add_argument("--request-count", type=int, default=40)
    parser.add_argument("--request-timeout", type=int, default=10)
    parser.add_argument("--access-log-timeout", type=int, default=900)
    parser.add_argument("--access-log-poll-interval", type=int, default=30)
    parser.add_argument("--health-timeout", type=int, default=600)
    parser.add_argument("--health-interval", type=int, default=15)
    parser.add_argument("--wait-delay", type=int, default=15)
    parser.add_argument("--wait-attempts", type=int, default=40)
    parser.add_argument("--apply", action="store_true", help="Zezwala na utworzenie albo zmianę ALB")
    parser.add_argument("--confirm", action="store_true", help="Potwierdza świadomy setup")
    return parser


def print_report(report: dict[str, Any]) -> None:
    print(f"Weryfikacja: {report['verification']}")
    print(f"Żądania: {report['requests']}")
    for identifier, count in report["counts"].items():
        print(f"{identifier}: {count} ({report['shares_percent'][identifier]}%)")
    print(f"Równomierny rozkład (30-70% na target): {'tak' if report['balanced'] else 'nie'}")


def require_balanced(report: dict[str, Any]) -> None:
    if not report["balanced"]:
        raise RuntimeError("Test wykrył nierównomierny rozkład ruchu między targetami.")


def validate_test_arguments(args: argparse.Namespace) -> None:
    if not args.dns_name or len(args.expected_instance_id) != 2:
        raise ValueError("Test wymaga --dns-name i dokładnie dwóch --expected-instance-id.")
    if len(set(args.expected_instance_id)) != 2:
        raise ValueError("Identyfikatory oczekiwanych instancji muszą być różne.")
    if not args.access_log_bucket or "/" in args.access_log_bucket:
        raise ValueError("Test wymaga nazwy istniejącego --access-log-bucket.")
    normalize_log_prefix(args.access_log_prefix)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.request_count < 2 or args.request_timeout < 1:
            raise ValueError("Test wymaga co najmniej dwóch żądań i dodatniego timeoutu.")
        if not args.path.startswith("/"):
            raise ValueError("--path musi zaczynać się od '/'.")
        if min(
            args.access_log_timeout,
            args.access_log_poll_interval,
            args.health_timeout,
            args.health_interval,
            args.wait_delay,
            args.wait_attempts,
        ) < 1:
            raise ValueError("Timeouty i interwały muszą być dodatnie.")
        if args.action == "test":
            validate_test_arguments(args)
            _elbv2, ec2, s3 = make_clients(args.region, args.profile)
            report = test_distribution(
                args.dns_name,
                args.expected_instance_id,
                ec2=ec2,
                s3=s3,
                access_log_bucket=args.access_log_bucket,
                access_log_prefix=args.access_log_prefix,
                path=args.path,
                requests_count=args.request_count,
                request_timeout=args.request_timeout,
                access_log_timeout=args.access_log_timeout,
                access_log_poll_interval=args.access_log_poll_interval,
            )
            print_report(report)
            require_balanced(report)
            return 0

        require_confirmation(args)
        validate_name(args.name, "--name")
        validate_name(args.target_group_name, "--target-group-name")
        if not args.vpc_id or len(set(args.subnet_id)) != 2 or len(args.subnet_id) != 2:
            raise ValueError("Setup wymaga --vpc-id i dokładnie dwóch różnych --subnet-id.")
        if not args.security_group_id or len(args.instance_id) != 2 or len(set(args.instance_id)) != 2:
            raise ValueError("Setup wymaga grupy bezpieczeństwa i dokładnie dwóch różnych --instance-id.")
        if not 1 <= args.target_port <= 65535 or not args.health_path.startswith("/"):
            raise ValueError("Nieprawidłowy port targetu lub ścieżka health check.")
        if not args.access_log_bucket or "/" in args.access_log_bucket:
            raise ValueError("Setup wymaga istniejącego --access-log-bucket z polityką dla ALB.")
        normalize_log_prefix(args.access_log_prefix)

        client, ec2, s3 = make_clients(args.region, args.profile)
        load_balancer = ensure_load_balancer(client, args.name, args.subnet_id, args.security_group_id)
        client.get_waiter("load_balancer_available").wait(
            LoadBalancerArns=[load_balancer["LoadBalancerArn"]],
            WaiterConfig={"Delay": args.wait_delay, "MaxAttempts": args.wait_attempts},
        )
        load_balancer = find_load_balancer(client, args.name)
        if load_balancer is None:
            raise RuntimeError("ALB zniknął przed zakończeniem setupu.")
        configure_access_logs(client, load_balancer["LoadBalancerArn"], args.access_log_bucket, args.access_log_prefix)
        target_group = ensure_target_group(
            client, args.target_group_name, args.vpc_id, args.target_port, args.health_path
        )
        client.register_targets(
            TargetGroupArn=target_group["TargetGroupArn"],
            Targets=[{"Id": identifier, "Port": args.target_port} for identifier in args.instance_id],
        )
        listener = ensure_listener(client, load_balancer["LoadBalancerArn"], target_group["TargetGroupArn"])
        wait_for_healthy_targets(
            client,
            target_group["TargetGroupArn"],
            args.instance_id,
            args.target_port,
            args.health_timeout,
            args.health_interval,
        )
        report = test_distribution(
            load_balancer["DNSName"],
            args.instance_id,
            ec2=ec2,
            s3=s3,
            access_log_bucket=args.access_log_bucket,
            access_log_prefix=args.access_log_prefix,
            path=args.path,
            requests_count=args.request_count,
            request_timeout=args.request_timeout,
            access_log_timeout=args.access_log_timeout,
            access_log_poll_interval=args.access_log_poll_interval,
        )
        print(f"ALB ARN: {load_balancer['LoadBalancerArn']}")
        print(f"Listener ARN: {listener['ListenerArn']}")
        print_report(report)
        require_balanced(report)
        return 0
    except (NoCredentialsError, PartialCredentialsError):
        print("Brak poprawnych poświadczeń AWS.")
        return 2
    except (ClientError, WaiterError, BotoCoreError, RuntimeError, ValueError) as error:
        print(f"ALB setup/test nie został ukończony: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
