import argparse
import json
from pathlib import Path


ENVIRONMENTS = ("dev", "staging", "production")
FIELDS = ("region", "instance_type", "db_size")
DEFAULT_CONFIGURATIONS = {
    "dev": {"region": "eu-central-1", "instance_type": "t3.micro", "db_size": "20 GB"},
    "staging": {
        "region": "eu-central-1",
        "instance_type": "t3.small",
        "db_size": "50 GB",
    },
    "production": {
        "region": "eu-west-1",
        "instance_type": "t3.medium",
        "db_size": "100 GB",
    },
}


class ConfigManager:
    def __init__(self, config_path: str | Path):
        self.config_path = Path(config_path)
        self.configurations = self._load_or_create()

    def _load_or_create(self) -> dict:
        if not self.config_path.exists():
            configurations = json.loads(json.dumps(DEFAULT_CONFIGURATIONS))
            self._save(configurations)
            return configurations

        try:
            configurations = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Nie można odczytać konfiguracji: {error}") from error

        self._validate(configurations)
        return configurations

    def _save(self, configurations: dict) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.config_path.with_suffix(self.config_path.suffix + ".tmp")
        try:
            temporary_path.write_text(
                json.dumps(configurations, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            temporary_path.replace(self.config_path)
        except OSError:
            temporary_path.unlink(missing_ok=True)
            raise

    @staticmethod
    def _validate(configurations: dict) -> None:
        if not isinstance(configurations, dict):
            raise ValueError("Konfiguracja musi być obiektem JSON.")

        for environment in ENVIRONMENTS:
            configuration = configurations.get(environment)
            if not isinstance(configuration, dict):
                raise ValueError(f"Brak konfiguracji środowiska: {environment}.")
            missing = [field for field in FIELDS if not configuration.get(field)]
            if missing:
                raise ValueError(
                    f"Brak pól w środowisku {environment}: {', '.join(missing)}."
                )

    def _environment(self, environment: str) -> dict:
        if environment not in ENVIRONMENTS:
            raise ValueError(f"Nieznane środowisko: {environment}.")
        return self.configurations[environment]

    def deploy(self, environment: str) -> dict:
        configuration = self._environment(environment)
        print(f"Plan wdrożenia dla {environment}:")
        print(f"- EC2 {configuration['instance_type']} w {configuration['region']}")
        print(f"- Baza danych o rozmiarze {configuration['db_size']}")
        return configuration.copy()

    def compare(self, env1: str, env2: str) -> dict:
        first = self._environment(env1)
        second = self._environment(env2)
        differences = {
            field: {env1: first[field], env2: second[field]}
            for field in FIELDS
            if first[field] != second[field]
        }
        if differences:
            print(f"Różnice: {env1} / {env2}")
            for field, values in differences.items():
                print(f"- {field}: {values[env1]} / {values[env2]}")
        else:
            print("Środowiska mają identyczną konfigurację.")
        return differences


def main() -> int:
    parser = argparse.ArgumentParser(description="Menedżer konfiguracji środowisk.")
    parser.add_argument("--config", default="environments.json", help="Plik JSON")
    commands = parser.add_subparsers(dest="command", required=True)
    deploy = commands.add_parser("deploy")
    deploy.add_argument("environment", choices=ENVIRONMENTS)
    compare = commands.add_parser("compare")
    compare.add_argument("env1", choices=ENVIRONMENTS)
    compare.add_argument("env2", choices=ENVIRONMENTS)
    args = parser.parse_args()

    try:
        manager = ConfigManager(args.config)
        if args.command == "deploy":
            manager.deploy(args.environment)
        else:
            manager.compare(args.env1, args.env2)
    except (OSError, ValueError) as error:
        print(f"Błąd konfiguracji: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
