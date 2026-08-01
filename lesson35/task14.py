"""Plan Disaster Recovery: DNS failover, S3 CRR i kopia snapshotu RDS."""

from __future__ import annotations

import argparse
import hashlib
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


PRIMARY_REGION = "eu-central-1"
BACKUP_REGION = "us-east-1"


def require_apply(args: argparse.Namespace) -> None:
    if not args.apply or args.confirm != "DISASTER-RECOVERY":
        raise SystemExit("Wymagane: --apply --confirm DISASTER-RECOVERY")


def zone_id(value: str) -> str:
    return value.rsplit("/", 1)[-1]


def caller_reference(prefix: str) -> str:
    return f"lesson36-{prefix}-{uuid.uuid4()}"


def primary_health_check_reference(fqdn: str, health_path: str, port: int) -> str:
    """Staly CallerReference pozwala AWS zwrocic ten sam health check."""
    material = f"{fqdn.rstrip('.').lower()}|{health_path}|{port}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
    return f"lesson36-primary-health-{digest}"


def rds_identifier(prefix: str, value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9-]", "-", value.lower()).strip("-")
    if not cleaned or not cleaned[0].isalpha():
        cleaned = "snapshot"
    return f"{prefix}-{cleaned}"[:63].rstrip("-")


def ensure_bucket_region(s3: Any, bucket: str, expected_region: str) -> None:
    location = s3.get_bucket_location(Bucket=bucket).get("LocationConstraint")
    actual_region = "us-east-1" if location is None else location
    if actual_region == "EU":
        actual_region = "eu-west-1"
    if actual_region != expected_region:
        raise ValueError(
            f"Bucket {bucket} jest w {actual_region}, a powinien byc w {expected_region}."
        )


def configure_s3_replication(
    primary_s3: Any,
    backup_s3: Any,
    primary_bucket: str,
    backup_bucket: str,
    replication_role_arn: str,
) -> None:
    """Wlacza versioning po obu stronach i regule CRR dla wszystkich obiektow."""
    ensure_bucket_region(primary_s3, primary_bucket, PRIMARY_REGION)
    ensure_bucket_region(backup_s3, backup_bucket, BACKUP_REGION)
    primary_s3.put_bucket_versioning(
        Bucket=primary_bucket, VersioningConfiguration={"Status": "Enabled"}
    )
    backup_s3.put_bucket_versioning(
        Bucket=backup_bucket, VersioningConfiguration={"Status": "Enabled"}
    )
    primary_s3.put_bucket_replication(
        Bucket=primary_bucket,
        ReplicationConfiguration={
            "Role": replication_role_arn,
            "Rules": [
                {
                    "ID": "replicate-to-us-east-1",
                    "Priority": 1,
                    "Status": "Enabled",
                    "Filter": {},
                    "DeleteMarkerReplication": {"Status": "Enabled"},
                    "Destination": {"Bucket": f"arn:aws:s3:::{backup_bucket}"},
                }
            ],
        },
    )


def create_primary_health_check(
    route53: Any, fqdn: str, health_path: str, port: int, reference: str
) -> str:
    response = route53.create_health_check(
        CallerReference=reference,
        HealthCheckConfig={
            "Type": "HTTPS",
            "FullyQualifiedDomainName": fqdn,
            "ResourcePath": health_path,
            "Port": port,
            "RequestInterval": 30,
            "FailureThreshold": 3,
            "EnableSNI": True,
        },
    )
    return response["HealthCheck"]["Id"]


def find_health_check_by_reference(route53: Any, reference: str) -> str | None:
    paginator = route53.get_paginator("list_health_checks")
    for page in paginator.paginate():
        for health_check in page.get("HealthChecks", []):
            if health_check.get("CallerReference") == reference:
                return health_check["Id"]
    return None


def validate_primary_health_check(
    route53: Any, health_check_id: str, fqdn: str, health_path: str, port: int
) -> None:
    config = route53.get_health_check(HealthCheckId=health_check_id)[
        "HealthCheck"
    ]["HealthCheckConfig"]
    if (
        config.get("Type") != "HTTPS"
        or config.get("FullyQualifiedDomainName", "").rstrip(".").lower()
        != fqdn.rstrip(".").lower()
        or config.get("ResourcePath") != health_path
        or config.get("Port", 443) != port
    ):
        raise ValueError("Podany health check nie odpowiada primary endpointowi.")


def get_or_create_primary_health_check(
    route53: Any, args: argparse.Namespace
) -> tuple[str, bool]:
    if args.primary_health_check_id:
        validate_primary_health_check(
            route53,
            args.primary_health_check_id,
            args.primary_health_fqdn,
            args.health_path,
            args.health_port,
        )
        return args.primary_health_check_id, False
    reference = primary_health_check_reference(
        args.primary_health_fqdn, args.health_path, args.health_port
    )
    existing = find_health_check_by_reference(route53, reference)
    if existing:
        return existing, False
    return (
        create_primary_health_check(
            route53,
            args.primary_health_fqdn,
            args.health_path,
            args.health_port,
            reference,
        ),
        True,
    )


def validate_public_hosted_zone(
    route53: Any, hosted_zone_id: str, record_names: list[str]
) -> None:
    hosted_zone = route53.get_hosted_zone(Id=zone_id(hosted_zone_id))["HostedZone"]
    zone_name = hosted_zone["Name"].rstrip(".").lower()
    if hosted_zone.get("Config", {}).get("PrivateZone"):
        raise ValueError("Symulacja DNS wymaga publicznej Hosted Zone.")
    for record_name in record_names:
        normalized = record_name.rstrip(".").lower()
        if normalized != zone_name and not normalized.endswith(f".{zone_name}"):
            raise ValueError(f"Rekord {record_name} nie nalezy do Hosted Zone {zone_name}.")


def primary_health_check_is_referenced(
    route53: Any, hosted_zone_id: str, health_check_id: str
) -> bool:
    paginator = route53.get_paginator("list_resource_record_sets")
    for page in paginator.paginate(HostedZoneId=zone_id(hosted_zone_id)):
        if any(
            record.get("HealthCheckId") == health_check_id
            for record in page.get("ResourceRecordSets", [])
        ):
            return True
    return False


def cleanup_unattached_primary_health_check(
    route53: Any, hosted_zone_id: str, health_check_id: str
) -> bool:
    """Usuwa tylko nowy health check, ktory nie zostal podlaczony do DNS."""
    if primary_health_check_is_referenced(route53, hosted_zone_id, health_check_id):
        return False
    route53.delete_health_check(HealthCheckId=health_check_id)
    return True


def alias_failover_record(
    record_name: str,
    set_identifier: str,
    failover: str,
    target_zone_id: str,
    target_dns_name: str,
    health_check_id: str | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "Name": record_name,
        "Type": "A",
        "SetIdentifier": set_identifier,
        "Failover": failover,
        "AliasTarget": {
            "HostedZoneId": zone_id(target_zone_id),
            "DNSName": target_dns_name,
            "EvaluateTargetHealth": True,
        },
    }
    if health_check_id:
        record["HealthCheckId"] = health_check_id
    return record


def change_records(
    route53: Any, hosted_zone_id: str, action: str, records: list[dict[str, Any]]
) -> str:
    response = route53.change_resource_record_sets(
        HostedZoneId=zone_id(hosted_zone_id),
        ChangeBatch={
            "Comment": "lesson36 DR failover",
            "Changes": [
                {"Action": action, "ResourceRecordSet": record} for record in records
            ],
        },
    )
    return response["ChangeInfo"]["Id"]


def wait_for_change(route53: Any, change_id: str, timeout_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        status = route53.get_change(Id=change_id)["ChangeInfo"]["Status"]
        if status == "INSYNC":
            return
        time.sleep(2)
    raise TimeoutError("Route53 nie potwierdzil propagacji zmiany.")


def configure_failover_records(
    route53: Any,
    args: argparse.Namespace,
    health_check_id: str,
) -> str:
    records = [
        alias_failover_record(
            args.record_name,
            "primary-eu-central-1",
            "PRIMARY",
            args.primary_alb_zone_id,
            args.primary_alb_dns,
            health_check_id,
        ),
        alias_failover_record(
            args.record_name,
            "secondary-us-east-1",
            "SECONDARY",
            args.backup_alb_zone_id,
            args.backup_alb_dns,
        ),
    ]
    return change_records(route53, args.hosted_zone_id, "UPSERT", records)


def wait_for_snapshot(rds: Any, snapshot_id: str, timeout_seconds: int) -> None:
    waiter = rds.get_waiter("db_snapshot_available")
    waiter.wait(
        DBSnapshotIdentifier=snapshot_id,
        WaiterConfig={"Delay": 30, "MaxAttempts": max(1, timeout_seconds // 30)},
    )


def source_snapshot(
    primary_rds: Any, args: argparse.Namespace
) -> tuple[str, dict[str, Any]]:
    if args.source_snapshot_arn:
        response = primary_rds.describe_db_snapshots(
            DBSnapshotIdentifier=args.source_snapshot_arn
        )
        snapshots = response.get("DBSnapshots", [])
        if not snapshots:
            raise ValueError("Nie znaleziono podanego snapshotu RDS.")
        snapshot = snapshots[0]
        if snapshot.get("Status") != "available":
            raise RuntimeError("Podany snapshot RDS nie jest jeszcze dostepny.")
        return snapshot["DBSnapshotArn"], snapshot

    snapshot_id = args.source_snapshot_id or rds_identifier(
        "dr", f"{args.db_instance_id}-{datetime.now(timezone.utc):%Y%m%d%H%M%S}"
    )
    response = primary_rds.create_db_snapshot(
        DBInstanceIdentifier=args.db_instance_id,
        DBSnapshotIdentifier=snapshot_id,
        Tags=[{"Key": "Purpose", "Value": "lesson36-disaster-recovery"}],
    )
    snapshot = response["DBSnapshot"]
    wait_for_snapshot(primary_rds, snapshot_id, args.snapshot_timeout_seconds)
    details = primary_rds.describe_db_snapshots(DBSnapshotIdentifier=snapshot_id)
    return details["DBSnapshots"][0]["DBSnapshotArn"], details["DBSnapshots"][0]


def copy_snapshot_to_backup(
    primary_rds: Any, backup_rds: Any, args: argparse.Namespace
) -> str:
    source_arn, snapshot = source_snapshot(primary_rds, args)
    if snapshot.get("Encrypted") and not args.destination_kms_key_id:
        raise ValueError("Dla szyfrowanego snapshotu podaj --destination-kms-key-id.")
    target_id = args.target_snapshot_id or rds_identifier(
        "dr-copy", f"{args.db_instance_id}-{datetime.now(timezone.utc):%Y%m%d%H%M%S}"
    )
    request: dict[str, Any] = {
        "SourceDBSnapshotIdentifier": source_arn,
        "TargetDBSnapshotIdentifier": target_id,
        "SourceRegion": PRIMARY_REGION,
        "CopyTags": True,
        "Tags": [{"Key": "Purpose", "Value": "lesson36-disaster-recovery"}],
    }
    if args.destination_kms_key_id:
        request["KmsKeyId"] = args.destination_kms_key_id
    backup_rds.copy_db_snapshot(**request)
    wait_for_snapshot(backup_rds, target_id, args.snapshot_timeout_seconds)
    return target_id


def answer(route53: Any, hosted_zone_id: str, record_name: str) -> tuple[str, ...]:
    response = route53.test_dns_answer(
        HostedZoneId=zone_id(hosted_zone_id), RecordName=record_name, RecordType="A"
    )
    if response.get("ResponseCode") != "NOERROR":
        return ()
    return tuple(sorted(response.get("RecordData", [])))


def wait_for_answer(
    route53: Any,
    hosted_zone_id: str,
    record_name: str,
    timeout_seconds: int,
    different_from: tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        current = answer(route53, hosted_zone_id, record_name)
        if current and (different_from is None or current != different_from):
            return current
        time.sleep(2)
    raise TimeoutError("Nie otrzymano oczekiwanej odpowiedzi Route53.")


def wait_for_backup_http(
    url: str,
    header_name: str,
    expected_value: str,
    timeout_seconds: int,
) -> None:
    """Potwierdza, że żądanie przez rekord testowy dotarło do backup regionu."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            request = Request(url, headers={"Cache-Control": "no-cache"})
            with urlopen(request, timeout=10) as response:
                value = response.headers.get(header_name, "")
                if 200 <= response.status < 300 and value.lower() == expected_value.lower():
                    return
        except (HTTPError, URLError, TimeoutError, OSError):
            pass
        time.sleep(2)
    raise TimeoutError("Żądanie przez rekord testowy nie potwierdziło endpointu backup.")


def create_forced_unhealthy_check(route53: Any, source_health_check_id: str) -> str:
    """Calculated check z progiem > liczba dzieci bezpiecznie symuluje awarie."""
    response = route53.create_health_check(
        CallerReference=caller_reference("simulation-health"),
        HealthCheckConfig={
            "Type": "CALCULATED",
            "ChildHealthChecks": [source_health_check_id],
            "HealthThreshold": 2,
        },
    )
    return response["HealthCheck"]["Id"]


def simulate_primary_outage(
    route53: Any, args: argparse.Namespace, source_health_check_id: str
) -> float:
    """Testuje tymczasowy rekord; nie zatrzymuje zadnego zasobu primary."""
    token = uuid.uuid4().hex[:12]
    primary = alias_failover_record(
        args.simulation_record_name,
        f"simulation-primary-{token}",
        "PRIMARY",
        args.primary_alb_zone_id,
        args.primary_alb_dns,
    )
    secondary = alias_failover_record(
        args.simulation_record_name,
        f"simulation-secondary-{token}",
        "SECONDARY",
        args.backup_alb_zone_id,
        args.backup_alb_dns,
    )
    forced_check_id: str | None = None
    changed_primary: dict[str, Any] | None = None
    records_created = False
    try:
        initial_change = change_records(
            route53, args.hosted_zone_id, "UPSERT", [primary, secondary]
        )
        records_created = True
        wait_for_change(route53, initial_change, args.dns_timeout_seconds)
        baseline = wait_for_answer(
            route53,
            args.hosted_zone_id,
            args.simulation_record_name,
            args.dns_timeout_seconds,
        )
        forced_check_id = create_forced_unhealthy_check(route53, source_health_check_id)
        changed_primary = dict(primary)
        changed_primary["HealthCheckId"] = forced_check_id
        started = time.monotonic()
        failure_change = change_records(
            route53, args.hosted_zone_id, "UPSERT", [changed_primary]
        )
        wait_for_change(route53, failure_change, args.dns_timeout_seconds)
        wait_for_answer(
            route53,
            args.hosted_zone_id,
            args.simulation_record_name,
            args.dns_timeout_seconds,
            different_from=baseline,
        )
        wait_for_backup_http(
            args.simulation_probe_url,
            args.backup_identity_header,
            args.backup_identity_value,
            args.dns_timeout_seconds,
        )
        return time.monotonic() - started
    finally:
        if records_created:
            records_to_delete = [secondary]
            if changed_primary is not None:
                records_to_delete.append(changed_primary)
            else:
                records_to_delete.append(primary)
            change_id = change_records(
                route53, args.hosted_zone_id, "DELETE", records_to_delete
            )
            wait_for_change(route53, change_id, args.dns_timeout_seconds)
        if forced_check_id and records_created:
            route53.delete_health_check(HealthCheckId=forced_check_id)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Konfiguruje DR eu-central-1 -> us-east-1.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm")
    parser.add_argument("--profile")
    parser.add_argument("--hosted-zone-id", required=True)
    parser.add_argument("--record-name", required=True)
    parser.add_argument("--simulation-record-name", required=True)
    parser.add_argument("--simulation-probe-url", required=True)
    parser.add_argument("--backup-identity-header", default="X-Region")
    parser.add_argument("--backup-identity-value", default=BACKUP_REGION)
    parser.add_argument("--primary-alb-dns", required=True)
    parser.add_argument("--primary-alb-zone-id", required=True)
    parser.add_argument("--backup-alb-dns", required=True)
    parser.add_argument("--backup-alb-zone-id", required=True)
    parser.add_argument("--primary-health-fqdn", required=True)
    parser.add_argument("--primary-health-check-id")
    parser.add_argument("--health-path", default="/health")
    parser.add_argument("--health-port", type=int, default=443)
    parser.add_argument("--primary-bucket", required=True)
    parser.add_argument("--backup-bucket", required=True)
    parser.add_argument("--replication-role-arn", required=True)
    parser.add_argument("--db-instance-id", required=True)
    parser.add_argument("--source-snapshot-arn")
    parser.add_argument("--source-snapshot-id")
    parser.add_argument("--target-snapshot-id")
    parser.add_argument("--destination-kms-key-id")
    parser.add_argument("--dns-timeout-seconds", type=int, default=300)
    parser.add_argument("--snapshot-timeout-seconds", type=int, default=3600)
    args = parser.parse_args()
    simulation_hostname = urlparse(args.simulation_probe_url).hostname
    if (
        not args.health_path.startswith("/")
        or not 1 <= args.health_port <= 65535
        or args.dns_timeout_seconds < 1
        or args.snapshot_timeout_seconds < 30
        or args.record_name == args.simulation_record_name
        or not args.replication_role_arn.startswith("arn:")
        or urlparse(args.simulation_probe_url).scheme not in {"http", "https"}
        or not simulation_hostname
        or simulation_hostname.lower() != args.simulation_record_name.rstrip(".").lower()
        or not args.backup_identity_header.strip()
        or not args.backup_identity_value.strip()
    ):
        parser.error("Nieprawidlowe parametry health, DNS, endpointu testowego, timeoutu lub roli IAM.")
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
        session = boto3.Session(profile_name=args.profile)
        primary_s3 = session.client("s3", region_name=PRIMARY_REGION)
        backup_s3 = session.client("s3", region_name=BACKUP_REGION)
        route53 = session.client("route53")
        primary_rds = session.client("rds", region_name=PRIMARY_REGION)
        backup_rds = session.client("rds", region_name=BACKUP_REGION)
        validate_public_hosted_zone(
            route53,
            args.hosted_zone_id,
            [args.record_name, args.simulation_record_name],
        )
        configure_s3_replication(
            primary_s3,
            backup_s3,
            args.primary_bucket,
            args.backup_bucket,
            args.replication_role_arn,
        )
        primary_health_check_id, created_primary_health_check = (
            get_or_create_primary_health_check(route53, args)
        )
        records_submitted = False
        try:
            change_id = configure_failover_records(
                route53, args, primary_health_check_id
            )
            records_submitted = True
            wait_for_change(route53, change_id, args.dns_timeout_seconds)
            copied_snapshot = copy_snapshot_to_backup(primary_rds, backup_rds, args)
            switch_seconds = simulate_primary_outage(
                route53, args, primary_health_check_id
            )
        except (
            BotoCoreError,
            ClientError,
            OSError,
            RuntimeError,
            TimeoutError,
            ValueError,
        ):
            if created_primary_health_check and not records_submitted:
                cleanup_unattached_primary_health_check(
                    route53, args.hosted_zone_id, primary_health_check_id
                )
            raise
    except NoCredentialsError as error:
        raise SystemExit("Brak konfiguracji AWS credentials lub profilu.") from error
    except (BotoCoreError, ClientError, OSError, RuntimeError, TimeoutError, ValueError) as error:
        raise SystemExit(f"DR nie zostal w pelni potwierdzony: {error}") from error
    print(f"Snapshot skopiowany do {BACKUP_REGION}: {copied_snapshot}")
    print(f"Zmierzony czas bezpiecznej symulacji failover: {switch_seconds:.2f} s")


if __name__ == "__main__":
    main()
