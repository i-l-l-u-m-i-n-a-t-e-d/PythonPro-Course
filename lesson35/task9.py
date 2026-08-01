"""Multi-AZ RDS, test połączenia PostgreSQL i pomiar failover."""

from __future__ import annotations

import argparse
import json
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

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


@dataclass(frozen=True)
class DatabaseConnection:
    host: str
    port: int
    database: str
    username: str
    password: str
    connect_timeout: int


def make_clients(region: str | None, profile: str | None) -> tuple[Any, Any]:
    try:
        import boto3
    except ImportError as error:
        raise RuntimeError("Brakuje boto3. Zainstaluj je w używanym środowisku.") from error

    session = boto3.Session(region_name=region, profile_name=profile)
    return session.client("rds"), session.client("secretsmanager")


def validate_identifier(identifier: str) -> str:
    if not DB_IDENTIFIER_PATTERN.fullmatch(identifier) or identifier.endswith("-"):
        raise ValueError("--db-instance-id musi być prawidłowym identyfikatorem RDS.")
    return identifier


def error_code(error: ClientError) -> str:
    return error.response.get("Error", {}).get("Code", "")


def describe_instance(rds: Any, identifier: str) -> dict[str, Any]:
    response = rds.describe_db_instances(DBInstanceIdentifier=identifier)
    instances = response.get("DBInstances", [])
    if not instances:
        raise RuntimeError("RDS nie zwrócił wskazanej instancji.")
    return instances[0]


def read_secret(secrets: Any, secret_id: str) -> dict[str, str]:
    """Odczytuje hasło ze Secrets Manager, nie wyświetlając jego wartości."""
    response = secrets.get_secret_value(SecretId=secret_id)
    value = response.get("SecretString")
    if value is None and response.get("SecretBinary") is not None:
        binary = response["SecretBinary"]
        value = binary.decode("utf-8") if isinstance(binary, bytes) else str(binary)
    if not value:
        raise RuntimeError("Sekret nie zawiera SecretString ani SecretBinary.")

    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        decoded = {"password": value}
    if not isinstance(decoded, dict):
        raise RuntimeError("Sekret musi być hasłem albo JSON-em z polem password.")

    result = {key: str(item) for key, item in decoded.items() if item is not None}
    if not result.get("password"):
        raise RuntimeError("Sekret musi zawierać niepuste pole password.")
    return result


def wait_for_instance(rds: Any, identifier: str, delay: int, attempts: int) -> dict[str, Any]:
    rds.get_waiter("db_instance_available").wait(
        DBInstanceIdentifier=identifier,
        WaiterConfig={"Delay": delay, "MaxAttempts": attempts},
    )
    instance = describe_instance(rds, identifier)
    if instance.get("DBInstanceStatus") != "available":
        raise RuntimeError("Instancja RDS nie osiągnęła stanu available.")
    return instance


def create_multi_az_instance(
    rds: Any,
    *,
    identifier: str,
    subnet_group: str,
    security_group_ids: list[str],
    master_username: str,
    master_password: str,
    database_name: str,
    instance_class: str,
    allocated_storage: int,
    engine: str,
) -> dict[str, Any]:
    """Tworzy prywatną instancję Multi-AZ albo sprawdza zgodną istniejącą."""
    try:
        instance = describe_instance(rds, identifier)
    except ClientError as error:
        if error_code(error) != "DBInstanceNotFound":
            raise
        response = rds.create_db_instance(
            DBInstanceIdentifier=identifier,
            DBInstanceClass=instance_class,
            Engine=engine,
            AllocatedStorage=allocated_storage,
            DBName=database_name,
            MasterUsername=master_username,
            MasterUserPassword=master_password,
            DBSubnetGroupName=subnet_group,
            VpcSecurityGroupIds=security_group_ids,
            MultiAZ=True,
            PubliclyAccessible=False,
        )
        instance = response["DBInstance"]

    if not instance.get("MultiAZ"):
        raise RuntimeError("Istniejąca instancja nie ma włączonego Multi-AZ.")
    return instance


def connection_from_instance(
    instance: dict[str, Any],
    secret: dict[str, str],
    database_name: str,
    explicit_user: str | None,
    connect_timeout: int,
) -> DatabaseConnection:
    endpoint = instance.get("Endpoint") or {}
    host = endpoint.get("Address")
    port = endpoint.get("Port", 5432)
    username = explicit_user or secret.get("username")
    if not host or not username:
        raise RuntimeError("Potrzebne są endpoint RDS i użytkownik (--db-user lub username w sekrecie).")
    return DatabaseConnection(
        host=host,
        port=int(port),
        database=database_name,
        username=username,
        password=secret["password"],
        connect_timeout=connect_timeout,
    )


def test_postgres_connection(connection: DatabaseConnection) -> None:
    """Nawiązuje rzeczywiste połączenie i wykonuje nieszkodliwe SELECT 1."""
    try:
        import psycopg  # psycopg 3

        connect = psycopg.connect
    except ImportError:
        try:
            import psycopg2  # psycopg 2

            connect = psycopg2.connect
        except ImportError as error:
            raise RuntimeError("Zainstaluj psycopg lub psycopg2 do testu połączenia PostgreSQL.") from error

    database = connect(
        host=connection.host,
        port=connection.port,
        dbname=connection.database,
        user=connection.username,
        password=connection.password,
        connect_timeout=connection.connect_timeout,
    )
    try:
        with database.cursor() as cursor:
            cursor.execute("SELECT 1")
            if cursor.fetchone() != (1,):
                raise RuntimeError("Zapytanie kontrolne PostgreSQL zwróciło nieoczekiwany wynik.")
    finally:
        database.close()


def collect_probes(
    probe: Callable[[], None],
    stop: threading.Event,
    interval: float,
    samples: list[tuple[float, bool]],
) -> None:
    """Rejestruje sukces lub błąd kolejnych rzeczywistych prób połączenia."""
    while not stop.is_set():
        started = time.monotonic()
        try:
            probe()
            samples.append((time.monotonic(), True))
        except Exception:
            samples.append((time.monotonic(), False))
        stop.wait(max(0.0, interval - (time.monotonic() - started)))


def observed_outages(samples: list[tuple[float, bool]]) -> tuple[list[float], bool]:
    """Zlicza okresy od pierwszej porażki do pierwszego późniejszego sukcesu."""
    started_at: float | None = None
    periods: list[float] = []
    for timestamp, is_available in sorted(samples):
        if not is_available and started_at is None:
            started_at = timestamp
        elif is_available and started_at is not None:
            periods.append(timestamp - started_at)
            started_at = None
    return periods, started_at is not None


def perform_failover(
    rds: Any,
    *,
    identifier: str,
    probe: Callable[[], None],
    probe_interval: float,
    recovery_timeout: int,
    waiter_delay: int,
    waiter_attempts: int,
) -> dict[str, Any]:
    """Wywołuje ForceFailover i mierzy niedostępność widoczną dla klienta DB."""
    instance = describe_instance(rds, identifier)
    if not instance.get("MultiAZ"):
        raise RuntimeError("ForceFailover wymaga instancji RDS z Multi-AZ.")

    probe()  # Stan początkowy musi być dostępny, aby pomiar był wiarygodny.
    samples: list[tuple[float, bool]] = [(time.monotonic(), True)]
    stop = threading.Event()
    monitor = threading.Thread(
        target=collect_probes,
        args=(probe, stop, probe_interval, samples),
        daemon=True,
    )
    monitor.start()
    failover_started = time.monotonic()
    try:
        rds.reboot_db_instance(DBInstanceIdentifier=identifier, ForceFailover=True)
        api_returned = time.monotonic()
        wait_for_instance(rds, identifier, waiter_delay, waiter_attempts)

        deadline = time.monotonic() + recovery_timeout
        while True:
            try:
                probe()
                samples.append((time.monotonic(), True))
                break
            except Exception:
                samples.append((time.monotonic(), False))
                if time.monotonic() >= deadline:
                    raise RuntimeError("Połączenie z bazą nie wróciło przed upływem recovery timeout.")
                time.sleep(min(probe_interval, 1.0))
    finally:
        stop.set()
        monitor.join(timeout=max(5.0, probe_interval + 5.0))

    periods, still_down = observed_outages(samples)
    if still_down:
        raise RuntimeError("Monitor zakończył się podczas zaobserwowanej niedostępności.")
    return {
        "measurement": "od pierwszej nieudanej próby DB do pierwszej późniejszej udanej",
        "failover_api_return_seconds": round(api_returned - failover_started, 2),
        "observed_downtime_seconds": round(sum(periods), 2),
        "outage_segments_seconds": [round(period, 2) for period in periods],
        "probe_count": len(samples),
        "failure_observed": bool(periods),
    }


def require_confirmation(args: argparse.Namespace) -> None:
    if not (args.apply and args.confirm):
        raise RuntimeError("Ta operacja wymaga jednocześnie --apply --confirm.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Multi-AZ RDS z testem połączenia i ForceFailover")
    parser.add_argument("--action", choices=("create", "test", "failover"), required=True)
    parser.add_argument("--db-instance-id", required=True)
    parser.add_argument("--region", help="Region AWS lub konfiguracja domyślna profilu")
    parser.add_argument("--profile", help="Opcjonalny profil AWS")
    parser.add_argument("--secret-id", help="Sekret z password i opcjonalnie username")
    parser.add_argument("--db-user", help="Użytkownik DB, gdy nie ma go w sekrecie")
    parser.add_argument("--db-name", default="appdb")
    parser.add_argument("--master-username", help="Wymagany przy --action create")
    parser.add_argument("--subnet-group", help="Wymagany przy --action create")
    parser.add_argument("--security-group-id", action="append", default=[], help="Można podać wielokrotnie")
    parser.add_argument("--engine", default="postgres")
    parser.add_argument("--instance-class", default="db.t3.micro")
    parser.add_argument("--allocated-storage", type=int, default=20)
    parser.add_argument("--connect-timeout", type=int, default=5)
    parser.add_argument("--probe-interval", type=float, default=2.0)
    parser.add_argument("--recovery-timeout", type=int, default=900)
    parser.add_argument("--wait-delay", type=int, default=30)
    parser.add_argument("--wait-attempts", type=int, default=120)
    parser.add_argument("--apply", action="store_true", help="Zezwala na create lub failover")
    parser.add_argument("--confirm", action="store_true", help="Potwierdza kosztowną albo przerywającą operację")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        validate_identifier(args.db_instance_id)
        if args.connect_timeout < 1 or args.probe_interval <= 0 or args.recovery_timeout < 1:
            raise ValueError("Timeouty i interwał prób muszą być dodatnie.")
        if args.wait_delay < 1 or args.wait_attempts < 1 or args.allocated_storage < 20:
            raise ValueError("Nieprawidłowe parametry instancji lub waitera.")
        if args.action in {"create", "failover"}:
            require_confirmation(args)
        if args.action == "create" and not all(
            (args.secret_id, args.master_username, args.subnet_group, args.security_group_id)
        ):
            raise ValueError("Create wymaga --secret-id, --master-username, --subnet-group i --security-group-id.")
        if args.action in {"test", "failover"} and not args.secret_id:
            raise ValueError("Test i failover wymagają --secret-id.")

        rds, secrets = make_clients(args.region, args.profile)
        if args.action == "create":
            secret = read_secret(secrets, args.secret_id)
            instance = create_multi_az_instance(
                rds,
                identifier=args.db_instance_id,
                subnet_group=args.subnet_group,
                security_group_ids=args.security_group_id,
                master_username=args.master_username,
                master_password=secret["password"],
                database_name=args.db_name,
                instance_class=args.instance_class,
                allocated_storage=args.allocated_storage,
                engine=args.engine,
            )
            if instance.get("DBInstanceStatus") != "available":
                instance = wait_for_instance(rds, args.db_instance_id, args.wait_delay, args.wait_attempts)
            endpoint = (instance.get("Endpoint") or {}).get("Address", "brak endpointu")
            print(f"Multi-AZ RDS jest available. Endpoint: {endpoint}")
            return 0

        instance = describe_instance(rds, args.db_instance_id)
        connection = connection_from_instance(
            instance,
            read_secret(secrets, args.secret_id),
            args.db_name,
            args.db_user,
            args.connect_timeout,
        )
        if args.action == "test":
            test_postgres_connection(connection)
            print("Test połączenia PostgreSQL zakończony powodzeniem.")
            return 0

        report = perform_failover(
            rds,
            identifier=args.db_instance_id,
            probe=lambda: test_postgres_connection(connection),
            probe_interval=args.probe_interval,
            recovery_timeout=args.recovery_timeout,
            waiter_delay=args.wait_delay,
            waiter_attempts=args.wait_attempts,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (NoCredentialsError, PartialCredentialsError):
        print("Brak poprawnych poświadczeń AWS.")
        return 2
    except (ClientError, WaiterError, BotoCoreError, RuntimeError, ValueError) as error:
        print(f"Operacja RDS nie została ukończona: {error}")
        return 1
    except Exception as error:
        print(f"Operacja RDS nie została ukończona: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
