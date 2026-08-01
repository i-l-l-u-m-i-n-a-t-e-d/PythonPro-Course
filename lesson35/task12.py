"""Codzienny backup RDS, retencja siedmiu dni, e-mail i log plikowy."""

from __future__ import annotations

import argparse
import json
import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

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


RETENTION_DAYS = 7
SCHEDULE_EXPRESSION = "cron(0 2 * * ? *)"
SCHEDULE_TIMEZONE = "Europe/Warsaw"


def make_clients(region: str | None, profile: str | None = None) -> tuple[Any, Any, Any]:
    try:
        import boto3
    except ImportError as error:
        raise RuntimeError("Brakuje boto3. Zainstaluj je w używanym środowisku.") from error

    session = boto3.Session(region_name=region, profile_name=profile)
    return session.client("rds"), session.client("sns"), session.client("scheduler")


def make_logger(log_file: str) -> logging.Logger:
    """Każde wykonanie zapisuje przebieg operacji do wskazanego pliku."""
    path = Path(log_file).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("lesson36.rds_backup")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger


def error_code(error: ClientError) -> str:
    return error.response.get("Error", {}).get("Code", "")


def daily_snapshot_id(db_instance_identifier: str, now: datetime | None = None) -> str:
    timestamp = now or datetime.now(timezone.utc)
    return f"{db_instance_identifier}-daily-{timestamp:%Y%m%d}"


def find_snapshot(rds: Any, snapshot_id: str) -> dict[str, Any] | None:
    try:
        snapshots = rds.describe_db_snapshots(DBSnapshotIdentifier=snapshot_id).get("DBSnapshots", [])
    except ClientError as error:
        if error_code(error) == "DBSnapshotNotFound":
            return None
        raise
    return snapshots[0] if snapshots else None


def ensure_daily_snapshot(
    rds: Any,
    db_instance_identifier: str,
    logger: logging.Logger,
    *,
    wait_delay: int = 30,
    wait_attempts: int = 120,
) -> tuple[dict[str, Any], bool]:
    """Tworzy tylko jeden ręczny snapshot o danym dniu i czeka na available."""
    snapshot_id = daily_snapshot_id(db_instance_identifier)
    snapshot = find_snapshot(rds, snapshot_id)
    created = snapshot is None
    if created:
        logger.info("Tworzenie snapshotu %s", snapshot_id)
        snapshot = rds.create_db_snapshot(
            DBInstanceIdentifier=db_instance_identifier,
            DBSnapshotIdentifier=snapshot_id,
        )["DBSnapshot"]
    else:
        logger.info("Snapshot %s już istnieje", snapshot_id)

    if snapshot.get("Status") != "available":
        logger.info("Oczekiwanie na dostępność snapshotu %s", snapshot_id)
        rds.get_waiter("db_snapshot_available").wait(
            DBSnapshotIdentifier=snapshot_id,
            WaiterConfig={"Delay": wait_delay, "MaxAttempts": wait_attempts},
        )
        snapshot = find_snapshot(rds, snapshot_id)
    if snapshot is None or snapshot.get("Status") != "available":
        raise RuntimeError("Snapshot nie osiągnął stanu available.")
    logger.info("Snapshot %s jest available", snapshot_id)
    return snapshot, created


def manual_snapshots(rds: Any, db_instance_identifier: str) -> Iterable[dict[str, Any]]:
    """Pobiera wszystkie strony ręcznych snapshotów wskazanej instancji."""
    paginator = rds.get_paginator("describe_db_snapshots")
    for page in paginator.paginate(DBInstanceIdentifier=db_instance_identifier, SnapshotType="manual"):
        yield from page.get("DBSnapshots", [])


def as_utc(timestamp: datetime) -> datetime:
    return timestamp.replace(tzinfo=timezone.utc) if timestamp.tzinfo is None else timestamp.astimezone(timezone.utc)


def prune_old_snapshots(
    rds: Any,
    db_instance_identifier: str,
    logger: logging.Logger,
    *,
    now: datetime | None = None,
) -> list[str]:
    """Usuwa wyłącznie ręczne snapshoty starsze niż siedem dni."""
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=RETENTION_DAYS)
    deleted: list[str] = []
    for snapshot in manual_snapshots(rds, db_instance_identifier):
        created_at = snapshot.get("SnapshotCreateTime")
        snapshot_id = snapshot.get("DBSnapshotIdentifier")
        if not created_at or not snapshot_id or as_utc(created_at) >= cutoff:
            continue
        if snapshot.get("Status") != "available":
            logger.warning("Pomijam snapshot %s w stanie %s", snapshot_id, snapshot.get("Status"))
            continue
        logger.info("Usuwanie snapshotu starszego niż %s dni: %s", RETENTION_DAYS, snapshot_id)
        rds.delete_db_snapshot(DBSnapshotIdentifier=snapshot_id)
        deleted.append(snapshot_id)
    return deleted


def send_notification(sns: Any, topic_arn: str, db_instance_identifier: str, snapshot_id: str, deleted: list[str]) -> None:
    message = (
        f"Backup RDS {db_instance_identifier} zakończony. "
        f"Snapshot: {snapshot_id}. Usunięto snapshotów starszych niż {RETENTION_DAYS} dni: {len(deleted)}."
    )
    sns.publish(
        TopicArn=topic_arn,
        Subject=f"RDS backup completed: {db_instance_identifier}",
        Message=message,
    )


def run_backup(
    rds: Any,
    sns: Any,
    *,
    db_instance_identifier: str,
    sns_topic_arn: str,
    log_file: str,
    wait_delay: int = 30,
    wait_attempts: int = 120,
) -> dict[str, Any]:
    """Jedno pełne wykonanie: snapshot, czyszczenie, e-mail i zapis logu."""
    logger = make_logger(log_file)
    try:
        snapshot, created = ensure_daily_snapshot(
            rds,
            db_instance_identifier,
            logger,
            wait_delay=wait_delay,
            wait_attempts=wait_attempts,
        )
        deleted = prune_old_snapshots(rds, db_instance_identifier, logger)
        snapshot_id = snapshot["DBSnapshotIdentifier"]
        send_notification(sns, sns_topic_arn, db_instance_identifier, snapshot_id, deleted)
        logger.info("Wysłano powiadomienie SNS po zakończeniu backupu")
        return {
            "snapshot_id": snapshot_id,
            "snapshot_created": created,
            "deleted_snapshot_count": len(deleted),
            "log_file": str(Path(log_file).expanduser()),
        }
    except Exception:
        logger.exception("Backup RDS nie został ukończony")
        raise


def lambda_handler(event: dict[str, Any] | None, _context: Any) -> dict[str, Any]:
    """Handler Lambda wykonywany pojedynczo przez EventBridge Scheduler."""
    config = event or {}
    db_instance_identifier = config.get("db_instance_identifier") or os.environ.get("DB_INSTANCE_IDENTIFIER")
    sns_topic_arn = config.get("sns_topic_arn") or os.environ.get("SNS_TOPIC_ARN")
    if not db_instance_identifier or not sns_topic_arn:
        raise ValueError("Handler wymaga db_instance_identifier oraz sns_topic_arn.")
    region = config.get("region") or os.environ.get("AWS_REGION")
    rds, sns, _scheduler = make_clients(region)
    return run_backup(
        rds,
        sns,
        db_instance_identifier=db_instance_identifier,
        sns_topic_arn=sns_topic_arn,
        log_file=config.get("log_file", "/tmp/rds-backup.log"),
        wait_delay=int(config.get("wait_delay", 30)),
        wait_attempts=int(config.get("wait_attempts", 120)),
    )


def ensure_email_subscription(sns: Any, topic_name: str, email: str) -> tuple[str, str]:
    """Tworzy topic SNS i jedną subskrypcję e-mail wymagającą potwierdzenia odbiorcy."""
    topic_arn = sns.create_topic(Name=topic_name)["TopicArn"]
    paginator = sns.get_paginator("list_subscriptions_by_topic")
    for page in paginator.paginate(TopicArn=topic_arn):
        for subscription in page.get("Subscriptions", []):
            if subscription.get("Protocol") == "email" and subscription.get("Endpoint", "").lower() == email.lower():
                return topic_arn, subscription.get("SubscriptionArn", "pending confirmation")
    response = sns.subscribe(TopicArn=topic_arn, Protocol="email", Endpoint=email, ReturnSubscriptionArn=True)
    return topic_arn, response.get("SubscriptionArn", "pending confirmation")


def schedule_input(db_instance_identifier: str, sns_topic_arn: str) -> str:
    return json.dumps(
        {
            "db_instance_identifier": db_instance_identifier,
            "sns_topic_arn": sns_topic_arn,
            "wait_delay": 30,
            "wait_attempts": 120,
        }
    )


def ensure_daily_schedule(
    scheduler: Any,
    *,
    schedule_name: str,
    schedule_group: str,
    lambda_arn: str,
    role_arn: str,
    db_instance_identifier: str,
    sns_topic_arn: str,
) -> str:
    """UPSERT harmonogramu Scheduler codziennie o 02:00 Europe/Warsaw."""
    settings = {
        "Name": schedule_name,
        "GroupName": schedule_group,
        "ScheduleExpression": SCHEDULE_EXPRESSION,
        "ScheduleExpressionTimezone": SCHEDULE_TIMEZONE,
        "FlexibleTimeWindow": {"Mode": "OFF"},
        "State": "ENABLED",
        "Target": {
            "Arn": lambda_arn,
            "RoleArn": role_arn,
            "Input": schedule_input(db_instance_identifier, sns_topic_arn),
        },
    }
    try:
        scheduler.get_schedule(Name=schedule_name, GroupName=schedule_group)
    except ClientError as error:
        if error_code(error) not in {"ResourceNotFoundException", "ResourceNotFound"}:
            raise
        response = scheduler.create_schedule(**settings)
    else:
        response = scheduler.update_schedule(**settings)
    return response["ScheduleArn"]


def require_confirmation(args: argparse.Namespace) -> None:
    if not (args.apply and args.confirm):
        raise RuntimeError("Ta operacja wymaga jednocześnie --apply --confirm.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Automatyczny backup RDS o 02:00 Europe/Warsaw")
    parser.add_argument("--action", choices=("run", "schedule", "email"), required=True)
    parser.add_argument("--region", help="Region AWS lub konfiguracja domyślna profilu")
    parser.add_argument("--profile", help="Opcjonalny profil AWS")
    parser.add_argument("--db-instance-id", help="Wymagane przez run i schedule")
    parser.add_argument("--sns-topic-arn", help="Topic SNS do powiadomienia o wyniku backupu")
    parser.add_argument(
        "--log-file",
        default=str(Path(tempfile.gettempdir()) / "lesson36-rds-backup.log"),
        help="Plik logu dla --action run (domyślnie katalog tymczasowy)",
    )
    parser.add_argument("--wait-delay", type=int, default=30)
    parser.add_argument("--wait-attempts", type=int, default=120)
    parser.add_argument("--schedule-name", default="lesson36-rds-daily-backup")
    parser.add_argument("--schedule-group", default="default")
    parser.add_argument("--lambda-arn", help="Istniejący ARN Lambda handlera")
    parser.add_argument("--scheduler-role-arn", help="Istniejący IAM Role ARN dla Target Scheduler")
    parser.add_argument("--topic-name", default="lesson36-rds-backup")
    parser.add_argument("--email", help="Adres odbiorcy potwierdzający subskrypcję SNS")
    parser.add_argument("--apply", action="store_true", help="Zezwala na snapshoty, SNS lub harmonogram")
    parser.add_argument("--confirm", action="store_true", help="Potwierdza operację zmieniającą AWS")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        require_confirmation(args)
        if args.wait_delay < 1 or args.wait_attempts < 1:
            raise ValueError("Parametry waitera muszą być dodatnie.")
        rds, sns, scheduler = make_clients(args.region, args.profile)
        if args.action == "run":
            if not args.db_instance_id or not args.sns_topic_arn:
                raise ValueError("Run wymaga --db-instance-id i --sns-topic-arn.")
            result = run_backup(
                rds,
                sns,
                db_instance_identifier=args.db_instance_id,
                sns_topic_arn=args.sns_topic_arn,
                log_file=args.log_file,
                wait_delay=args.wait_delay,
                wait_attempts=args.wait_attempts,
            )
            print(f"Backup ukończony: {result['snapshot_id']}; usunięto: {result['deleted_snapshot_count']}")
            return 0
        if args.action == "email":
            if not args.email or "@" not in args.email or not args.topic_name.strip():
                raise ValueError("Email wymaga poprawnego --email i niepustego --topic-name.")
            topic_arn, subscription = ensure_email_subscription(sns, args.topic_name, args.email)
            print(f"Topic SNS: {topic_arn}; subskrypcja: {subscription}. Potwierdź e-mail od SNS.")
            return 0
        if not all((args.db_instance_id, args.sns_topic_arn, args.lambda_arn, args.scheduler_role_arn)):
            raise ValueError("Schedule wymaga DB, topic SNS, --lambda-arn i --scheduler-role-arn.")
        schedule_arn = ensure_daily_schedule(
            scheduler,
            schedule_name=args.schedule_name,
            schedule_group=args.schedule_group,
            lambda_arn=args.lambda_arn,
            role_arn=args.scheduler_role_arn,
            db_instance_identifier=args.db_instance_id,
            sns_topic_arn=args.sns_topic_arn,
        )
        print(f"Scheduler ustawiony na 02:00 {SCHEDULE_TIMEZONE}: {schedule_arn}")
        return 0
    except (NoCredentialsError, PartialCredentialsError):
        print("Brak poprawnych poświadczeń AWS.")
        return 2
    except (ClientError, WaiterError, BotoCoreError, RuntimeError, ValueError) as error:
        print(f"Backup/scheduler nie został ukończony: {error}")
        return 1
    except Exception as error:
        print(f"Backup/scheduler nie został ukończony: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
