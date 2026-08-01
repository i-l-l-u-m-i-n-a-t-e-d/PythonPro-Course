import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


DEFAULT_DATA_DIR = Path("dr_data")


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(log_file: str | Path, message: str, level: int = logging.INFO) -> None:
    path = Path(log_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"disaster_recovery.{path.resolve()}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    try:
        logger.log(level, message)
    finally:
        logger.removeHandler(handler)
        handler.close()


def _load_metadata(metadata_file: str | Path) -> dict:
    path = Path(metadata_file)
    if not path.exists():
        return {"snapshots": []}
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Nie można odczytać metadanych: {error}") from error
    if not isinstance(metadata, dict) or not isinstance(metadata.get("snapshots"), list):
        raise ValueError("Nieprawidłowy format metadanych snapshotów.")
    return metadata


def _save_metadata(metadata_file: str | Path, metadata: dict) -> None:
    path = Path(metadata_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    try:
        temporary_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary_path.replace(path)
    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise


def _find_snapshot(metadata: dict, snapshot_id: str) -> dict:
    for snapshot in metadata["snapshots"]:
        if snapshot.get("snapshot_id") == snapshot_id:
            return snapshot
    raise ValueError(f"Nie znaleziono snapshotu: {snapshot_id}.")


def _log_file(metadata_file: str | Path, log_file: str | Path | None) -> Path:
    return Path(log_file) if log_file else Path(metadata_file).with_name("operations.log")


def create_snapshot(
    metadata_file: str | Path = DEFAULT_DATA_DIR / "snapshots.json",
    source_region: str = "eu-central-1",
    log_file: str | Path | None = None,
) -> str:
    if not source_region:
        raise ValueError("Region źródłowy jest wymagany.")

    metadata = _load_metadata(metadata_file)
    snapshot_id = f"snapshot-{uuid4().hex[:12]}"
    snapshot = {
        "snapshot_id": snapshot_id,
        "created_at": _timestamp(),
        "source_region": source_region,
        "ec2_snapshot_id": f"ec2-{uuid4().hex[:12]}",
        "rds_snapshot_id": f"rds-{uuid4().hex[:12]}",
        "backup": None,
        "restore": None,
    }
    metadata["snapshots"].append(snapshot)
    _save_metadata(metadata_file, metadata)
    _log(
        _log_file(metadata_file, log_file),
        f"Utworzono symulowane snapshoty EC2 i RDS: {snapshot_id}.",
    )
    return snapshot_id


def store_backup_s3(
    snapshot_id: str,
    bucket_name: str = "dr-backups",
    backup_region: str = "eu-west-1",
    metadata_file: str | Path = DEFAULT_DATA_DIR / "snapshots.json",
    log_file: str | Path | None = None,
) -> str:
    if not bucket_name or not backup_region:
        raise ValueError("Bucket i region backupu są wymagane.")

    metadata = _load_metadata(metadata_file)
    snapshot = _find_snapshot(metadata, snapshot_id)
    if snapshot["source_region"] == backup_region:
        raise ValueError("Backup musi być zapisany w innym regionie.")

    key = f"backups/{snapshot_id}.json"
    backup = {
        "bucket": bucket_name,
        "region": backup_region,
        "key": key,
        "uri": f"s3://{bucket_name}/{key}",
        "uploaded_at": _timestamp(),
    }
    snapshot["backup"] = backup
    _save_metadata(metadata_file, metadata)
    _log(
        _log_file(metadata_file, log_file),
        f"Zasymulowano upload {snapshot_id} do {backup['uri']} w {backup_region}.",
    )
    return backup["uri"]


def restore_from_backup(
    snapshot_id: str,
    metadata_file: str | Path = DEFAULT_DATA_DIR / "snapshots.json",
    log_file: str | Path | None = None,
) -> dict:
    metadata = _load_metadata(metadata_file)
    snapshot = _find_snapshot(metadata, snapshot_id)
    if not snapshot.get("backup"):
        raise ValueError("Najpierw zapisz backup w drugim regionie.")

    restore = {
        "status": "restored",
        "restored_at": _timestamp(),
        "ec2_instance_id": f"restored-{snapshot['ec2_snapshot_id']}",
        "rds_instance_id": f"restored-{snapshot['rds_snapshot_id']}",
    }
    snapshot["restore"] = restore
    _save_metadata(metadata_file, metadata)
    _log(
        _log_file(metadata_file, log_file),
        f"Zasymulowano odtworzenie zasobów z {snapshot_id}.",
    )
    return restore


def test_recovery(
    metadata_file: str | Path = DEFAULT_DATA_DIR / "snapshots.json",
    log_file: str | Path | None = None,
) -> bool:
    snapshot_id = create_snapshot(metadata_file, log_file=log_file)
    store_backup_s3(snapshot_id, metadata_file=metadata_file, log_file=log_file)
    restore = restore_from_backup(snapshot_id, metadata_file, log_file)
    success = restore["status"] == "restored"
    _log(
        _log_file(metadata_file, log_file),
        f"Test recovery dla {snapshot_id}: {'OK' if success else 'BŁĄD'}.",
        logging.INFO if success else logging.ERROR,
    )
    return success


def main() -> int:
    parser = argparse.ArgumentParser(description="Symulator disaster recovery.")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    commands = parser.add_subparsers(dest="command", required=True)
    snapshot = commands.add_parser("snapshot")
    snapshot.add_argument("--source-region", default="eu-central-1")
    backup = commands.add_parser("backup")
    backup.add_argument("snapshot_id")
    backup.add_argument("--bucket", default="dr-backups")
    backup.add_argument("--region", default="eu-west-1")
    restore = commands.add_parser("restore")
    restore.add_argument("snapshot_id")
    commands.add_parser("test")
    args = parser.parse_args()

    metadata_file = Path(args.data_dir) / "snapshots.json"
    try:
        if args.command == "snapshot":
            print(create_snapshot(metadata_file, args.source_region))
        elif args.command == "backup":
            print(store_backup_s3(args.snapshot_id, args.bucket, args.region, metadata_file))
        elif args.command == "restore":
            print(restore_from_backup(args.snapshot_id, metadata_file))
        else:
            print("Test odtwarzania: OK" if test_recovery(metadata_file) else "Test: BŁĄD")
    except (OSError, ValueError) as error:
        print(f"Błąd disaster recovery: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
