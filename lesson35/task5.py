import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(command, timeout):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode:
        details = result.stderr.strip() or "AWS CLI nie zwróciło opisu błędu."
        raise RuntimeError(details)
    return result.stdout.strip()


def parse_arguments():
    parser = argparse.ArgumentParser(description="Zapisuje zasoby AWS do aws-resources.txt.")
    parser.add_argument(
        "--region",
        default=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"),
    )
    parser.add_argument("--profile")
    parser.add_argument("--output", type=Path, default=Path("aws-resources.txt"))
    parser.add_argument("--timeout", type=int, default=60)
    return parser.parse_args()


def main():
    args = parse_arguments()
    if not args.region:
        print("Podaj --region lub ustaw AWS_REGION.", file=sys.stderr)
        return 2
    if args.timeout <= 0:
        print("--timeout musi być dodatni.", file=sys.stderr)
        return 2
    aws = shutil.which("aws")
    if not aws:
        print("Nie znaleziono programu AWS CLI w PATH.", file=sys.stderr)
        return 1

    base = [aws, "--no-cli-pager", "--region", args.region]
    if args.profile:
        base.extend(["--profile", args.profile])
    commands = [
        ("EC2", base + ["ec2", "describe-instances", "--output", "json"]),
        (
            "RDS",
            base
            + [
                "rds",
                "describe-db-instances",
                "--query",
                "DBInstances[].{Identifier:DBInstanceIdentifier,Status:DBInstanceStatus}",
                "--output",
                "json",
            ],
        ),
        ("S3", base + ["s3api", "list-buckets", "--output", "json"]),
    ]

    try:
        sections = [f"[{name}]\n{run_command(command, args.timeout)}" for name, command in commands]
        args.output.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    except subprocess.TimeoutExpired:
        print("Przekroczono limit czasu polecenia AWS CLI.", file=sys.stderr)
        return 1
    except RuntimeError as error:
        print(f"Polecenie AWS CLI nie powiodło się: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"Nie można zapisać pliku wyjściowego: {error}", file=sys.stderr)
        return 1

    print(f"Zapisano wynik do {args.output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
