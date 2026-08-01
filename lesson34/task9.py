import argparse
import logging
import sys
from typing import Any

try:
    import boto3
    from botocore.exceptions import (
        BotoCoreError,
        ClientError,
        EndpointConnectionError,
        NoCredentialsError,
        NoRegionError,
        PartialCredentialsError,
    )
except ImportError:
    boto3 = None
    BotoCoreError = ClientError = EndpointConnectionError = Exception
    NoCredentialsError = NoRegionError = PartialCredentialsError = Exception


def configure_logger() -> logging.Logger:
    logger = logging.getLogger("auto_stop_ec2")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def stop_autostop_instances(
    ec2_client: Any, *, dry_run: bool = True, logger: logging.Logger | None = None
) -> list[str]:
    """Zatrzymuje działające instancje oznaczone tagiem AutoStop=true."""
    logger = logger or configure_logger()
    stopped: list[str] = []
    paginator = ec2_client.get_paginator("describe_instances")

    for page in paginator.paginate(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    ):
        for reservation in page.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                instance_id = instance["InstanceId"]
                tags = {tag["Key"]: tag.get("Value", "") for tag in instance.get("Tags", [])}
                if tags.get("AutoStop") != "true":
                    logger.info("Pomijam %s (AutoStop nie jest true).", instance_id)
                    continue

                if dry_run:
                    logger.info("Tryb podglądu: zatrzymałbym %s.", instance_id)
                    stopped.append(instance_id)
                    continue

                try:
                    ec2_client.stop_instances(InstanceIds=[instance_id])
                except ClientError as error:
                    logger.error("Nie zatrzymano %s: %s", instance_id, error)
                else:
                    logger.info("Wysłano polecenie zatrzymania %s.", instance_id)
                    stopped.append(instance_id)

    return stopped


def create_ec2_client(region: str | None) -> Any:
    if boto3 is None:
        raise RuntimeError("Brakuje boto3. Zainstaluj je poleceniem: python -m pip install boto3")
    return boto3.client("ec2", region_name=region)


def main() -> int:
    parser = argparse.ArgumentParser(description="Zatrzymuje EC2 z tagiem AutoStop=true.")
    parser.add_argument("--region", help="region AWS")
    parser.add_argument("--execute", action="store_true", help="naprawdę zatrzymaj instancje")
    args = parser.parse_args()
    logger = configure_logger()

    try:
        client = create_ec2_client(args.region)
        stop_autostop_instances(client, dry_run=not args.execute, logger=logger)
    except (NoCredentialsError, PartialCredentialsError):
        logger.error("Brakuje poprawnych poświadczeń AWS.")
        return 1
    except NoRegionError:
        logger.error("Podaj --region albo ustaw AWS_DEFAULT_REGION.")
        return 1
    except EndpointConnectionError:
        logger.error("Nie można połączyć się z usługą EC2.")
        return 1
    except (ClientError, BotoCoreError, RuntimeError) as error:
        logger.error("Operacja EC2 nie powiodła się: %s", error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
