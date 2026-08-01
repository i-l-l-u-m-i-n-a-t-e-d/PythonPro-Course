"""Tworzy Target Group HTTP:8000 z health checkiem /health."""

from __future__ import annotations

import argparse
import re
from typing import Any

try:
    from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, PartialCredentialsError
except ImportError:  # Komunikat o brakującym boto3 jest zwracany dopiero przy uruchomieniu.
    class BotoCoreError(Exception):
        pass

    class ClientError(Exception):
        pass

    class NoCredentialsError(Exception):
        pass

    class PartialCredentialsError(Exception):
        pass


NAME_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,30}[A-Za-z0-9])?$")


def make_elbv2_client(region: str | None, profile: str | None) -> Any:
    """Korzysta ze standardowego łańcucha poświadczeń AWS."""
    try:
        import boto3
    except ImportError as error:
        raise RuntimeError("Brakuje boto3. Zainstaluj je w używanym środowisku.") from error

    session = boto3.Session(region_name=region, profile_name=profile)
    return session.client("elbv2")


def validate_target_group_name(name: str) -> str:
    if not NAME_PATTERN.fullmatch(name) or len(name) > 32:
        raise ValueError("Nazwa Target Group musi mieć 1-32 znaki alfanumeryczne lub '-'.")
    return name


def is_not_found(error: ClientError) -> bool:
    return error.response.get("Error", {}).get("Code") == "TargetGroupNotFound"


def create_target_group(client: Any, name: str, vpc_id: str) -> dict[str, Any]:
    """Tworzy wymagany Target Group lub bezpiecznie wykorzystuje zgodny istniejący."""
    try:
        target_group = client.describe_target_groups(Names=[name])["TargetGroups"][0]
    except ClientError as error:
        if not is_not_found(error):
            raise
        response = client.create_target_group(
            Name=name,
            Protocol="HTTP",
            Port=8000,
            VpcId=vpc_id,
            TargetType="instance",
            HealthCheckEnabled=True,
            HealthCheckProtocol="HTTP",
            HealthCheckPath="/health",
            HealthCheckPort="traffic-port",
            HealthCheckIntervalSeconds=30,
            HealthCheckTimeoutSeconds=5,
            HealthyThresholdCount=2,
            UnhealthyThresholdCount=2,
            Matcher={"HttpCode": "200"},
        )
        target_group = response["TargetGroups"][0]

    required = {
        "Protocol": "HTTP",
        "Port": 8000,
        "HealthCheckPath": "/health",
        "HealthCheckIntervalSeconds": 30,
    }
    incompatible = [key for key, value in required.items() if target_group.get(key) != value]
    if target_group.get("VpcId") != vpc_id or incompatible:
        raise RuntimeError("Istniejący Target Group nie spełnia parametrów zadania.")
    return target_group


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Target Group HTTP:8000 z /health co 30 s")
    parser.add_argument("--vpc-id", required=True, help="Identyfikator VPC")
    parser.add_argument("--name", default="lesson36-http-8000", help="Nazwa Target Group")
    parser.add_argument("--region", help="Region AWS lub konfiguracja domyślna profilu")
    parser.add_argument("--profile", help="Opcjonalny profil AWS")
    parser.add_argument("--apply", action="store_true", help="Zezwala na utworzenie zasobu")
    parser.add_argument("--confirm", action="store_true", help="Potwierdza świadome utworzenie zasobu")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        validate_target_group_name(args.name)
        if not args.vpc_id.strip():
            raise ValueError("--vpc-id nie może być pusty.")
        if not (args.apply and args.confirm):
            print("Tryb planu: podaj jednocześnie --apply --confirm, aby utworzyć Target Group.")
            return 0
        target_group = create_target_group(
            make_elbv2_client(args.region, args.profile), args.name, args.vpc_id
        )
    except (NoCredentialsError, PartialCredentialsError):
        print("Brak poprawnych poświadczeń AWS.")
        return 2
    except (ClientError, BotoCoreError, RuntimeError, ValueError) as error:
        print(f"Nie utworzono Target Group: {error}")
        return 1

    print(f"Target Group ARN: {target_group['TargetGroupArn']}")
    print("HTTP:8000, health check: /health, interwał: 30 s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
