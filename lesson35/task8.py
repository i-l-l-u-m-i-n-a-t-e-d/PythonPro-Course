"""Tworzy Read Replica, czeka na jej dostępność i wypisuje endpoint."""

from __future__ import annotations

import argparse
import re
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


DB_IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,62}$")


def make_rds_client(region: str | None, profile: str | None) -> Any:
    try:
        import boto3
    except ImportError as error:
        raise RuntimeError("Brakuje boto3. Zainstaluj je w używanym środowisku.") from error

    session = boto3.Session(region_name=region, profile_name=profile)
    return session.client("rds")


def validate_identifier(identifier: str, option: str) -> str:
    if not DB_IDENTIFIER_PATTERN.fullmatch(identifier) or identifier.endswith("-"):
        raise ValueError(f"{option} musi być prawidłowym identyfikatorem instancji RDS.")
    return identifier


def is_instance_not_found(error: ClientError) -> bool:
    return error.response.get("Error", {}).get("Code") == "DBInstanceNotFound"


def describe_instance(client: Any, identifier: str) -> dict[str, Any] | None:
    try:
        return client.describe_db_instances(DBInstanceIdentifier=identifier)["DBInstances"][0]
    except ClientError as error:
        if is_instance_not_found(error):
            return None
        raise


def create_read_replica(
    client: Any,
    source_identifier: str,
    replica_identifier: str,
    wait_delay: int = 30,
    wait_attempts: int = 120,
) -> dict[str, Any]:
    """Tworzy replikę tylko wtedy, gdy wskazany identyfikator jeszcze nie istnieje."""
    replica = describe_instance(client, replica_identifier)
    if replica is None:
        client.create_db_instance_read_replica(
            DBInstanceIdentifier=replica_identifier,
            SourceDBInstanceIdentifier=source_identifier,
        )

    waiter = client.get_waiter("db_instance_available")
    waiter.wait(
        DBInstanceIdentifier=replica_identifier,
        WaiterConfig={"Delay": wait_delay, "MaxAttempts": wait_attempts},
    )
    replica = describe_instance(client, replica_identifier)
    if replica is None or replica.get("DBInstanceStatus") != "available":
        raise RuntimeError("Read Replica nie osiągnęła stanu available.")
    source = replica.get("ReadReplicaSourceDBInstanceIdentifier", "")
    if not source:
        raise RuntimeError("Wskazany identyfikator należy do instancji, która nie jest Read Replica.")
    source_suffix = source.rsplit(":", 1)[-1]
    if source and source != source_identifier and source_suffix != source_identifier:
        raise RuntimeError("Istniejąca replika należy do innej instancji źródłowej.")
    return replica


def endpoint_text(instance: dict[str, Any]) -> str:
    endpoint = instance.get("Endpoint") or {}
    address = endpoint.get("Address")
    port = endpoint.get("Port")
    if not address:
        raise RuntimeError("RDS nie zwrócił endpointu Read Replica.")
    return f"{address}:{port}" if port else address


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tworzenie i oczekiwanie na RDS Read Replica")
    parser.add_argument("--source-db-id", required=True, help="Istniejąca instancja źródłowa RDS")
    parser.add_argument("--replica-db-id", required=True, help="Identyfikator nowej Read Replica")
    parser.add_argument("--region", help="Region AWS lub konfiguracja domyślna profilu")
    parser.add_argument("--profile", help="Opcjonalny profil AWS")
    parser.add_argument("--wait-delay", type=int, default=30, help="Sekundy między próbami waitera")
    parser.add_argument("--wait-attempts", type=int, default=120, help="Maksymalna liczba prób waitera")
    parser.add_argument("--apply", action="store_true", help="Zezwala na utworzenie repliki")
    parser.add_argument("--confirm", action="store_true", help="Potwierdza świadome utworzenie repliki")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        validate_identifier(args.source_db_id, "--source-db-id")
        validate_identifier(args.replica_db_id, "--replica-db-id")
        if args.source_db_id == args.replica_db_id:
            raise ValueError("Identyfikator repliki musi być inny niż źródłowy.")
        if args.wait_delay < 1 or args.wait_attempts < 1:
            raise ValueError("Parametry waitera muszą być dodatnie.")
        if not (args.apply and args.confirm):
            print("Tryb planu: podaj jednocześnie --apply --confirm, aby utworzyć Read Replica.")
            return 0
        replica = create_read_replica(
            make_rds_client(args.region, args.profile),
            args.source_db_id,
            args.replica_db_id,
            args.wait_delay,
            args.wait_attempts,
        )
    except (NoCredentialsError, PartialCredentialsError):
        print("Brak poprawnych poświadczeń AWS.")
        return 2
    except (ClientError, WaiterError, BotoCoreError, RuntimeError, ValueError) as error:
        print(f"Nie utworzono Read Replica: {error}")
        return 1

    print(f"Read Replica jest available. Endpoint: {endpoint_text(replica)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
