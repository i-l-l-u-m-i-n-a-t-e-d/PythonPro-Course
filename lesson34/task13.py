import argparse
import base64
import binascii
import subprocess
import sys
from pathlib import Path

try:
    import boto3
    from botocore.exceptions import (
        BotoCoreError,
        ClientError,
        NoCredentialsError,
        PartialCredentialsError,
    )
except ImportError:
    boto3 = None

try:
    import paramiko
except ImportError:
    paramiko = None

try:
    import requests
except ImportError:
    requests = None


class PipelineError(RuntimeError):
    pass


def run_command(command: list[str], cwd: Path | None, timeout: int, input_text: str | None = None) -> None:
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as error:
        raise PipelineError(f"Nie znaleziono programu: {command[0]}") from error
    except subprocess.TimeoutExpired as error:
        raise PipelineError(f"Przekroczono limit czasu komendy: {command[0]}") from error

    if result.stdout:
        print(result.stdout, end="")
    if result.returncode != 0:
        details = result.stderr.strip() or "brak szczegółów"
        raise PipelineError(f"Komenda zakończyła się kodem {result.returncode}: {details}")


def update_repository(repo_url: str, repo_dir: Path, branch: str, timeout: int) -> None:
    if repo_dir.exists():
        if not (repo_dir / ".git").is_dir():
            raise PipelineError(f"Katalog {repo_dir} istnieje, ale nie jest repozytorium Git")
        run_command(["git", "-C", str(repo_dir), "fetch", "origin", branch], None, timeout)
        run_command(["git", "-C", str(repo_dir), "checkout", branch], None, timeout)
        run_command(["git", "-C", str(repo_dir), "pull", "--ff-only", "origin", branch], None, timeout)
        return

    repo_dir.parent.mkdir(parents=True, exist_ok=True)
    run_command(["git", "clone", "--branch", branch, "--single-branch", repo_url, str(repo_dir)], None, timeout)


def normalized_image_name(image: str) -> tuple[str, str]:
    last_part = image.rsplit("/", 1)[-1]
    if ":" in last_part:
        return image, last_part.rsplit(":", 1)[1]
    return f"{image}:latest", "latest"


def build_image(repo_dir: Path, image: str, timeout: int) -> tuple[str, str]:
    local_image, tag = normalized_image_name(image)
    run_command(["docker", "build", "--tag", local_image, str(repo_dir)], None, timeout)
    return local_image, tag


def push_to_ecr(local_image: str, repository: str, region: str, tag: str, timeout: int) -> str:
    if boto3 is None:
        raise PipelineError("Brak boto3. Zainstaluj pakiet: pip install boto3")

    try:
        ecr = boto3.client("ecr", region_name=region)
        repositories = ecr.describe_repositories(repositoryNames=[repository])
        repository_uri = repositories["repositories"][0]["repositoryUri"]
        authorization = ecr.get_authorization_token()["authorizationData"][0]
        username, password = base64.b64decode(authorization["authorizationToken"]).decode().split(":", 1)
    except NoCredentialsError as error:
        raise PipelineError("Brak poświadczeń AWS") from error
    except PartialCredentialsError as error:
        raise PipelineError("Niekompletne poświadczenia AWS") from error
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code", "ClientError")
        raise PipelineError(f"Błąd ECR: {code}") from error
    except (BotoCoreError, KeyError, IndexError, ValueError, UnicodeDecodeError, binascii.Error) as error:
        raise PipelineError(f"Nie można przygotować połączenia z ECR: {error}") from error

    registry = authorization["proxyEndpoint"].removeprefix("https://")
    remote_image = f"{repository_uri}:{tag}"
    run_command(["docker", "login", "--username", username, "--password-stdin", registry], None, timeout, password)
    run_command(["docker", "tag", local_image, remote_image], None, timeout)
    run_command(["docker", "push", remote_image], None, timeout)
    return remote_image


def run_ssh_command(
    host: str,
    username: str,
    key_path: Path,
    command: str,
    timeout: int,
    known_hosts: Path | None,
) -> None:
    if paramiko is None:
        raise PipelineError("Brak paramiko. Zainstaluj pakiet: pip install paramiko")
    if not key_path.is_file():
        raise PipelineError(f"Nie znaleziono klucza SSH: {key_path}")
    if known_hosts is not None and not known_hosts.is_file():
        raise PipelineError(f"Nie znaleziono pliku known_hosts: {known_hosts}")

    client = paramiko.SSHClient()
    client.load_system_host_keys()
    if known_hosts is not None:
        client.load_host_keys(str(known_hosts))
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    try:
        client.connect(
            hostname=host,
            username=username,
            key_filename=str(key_path),
            timeout=timeout,
            banner_timeout=timeout,
            auth_timeout=timeout,
            channel_timeout=timeout,
        )
        _, stdout, stderr = client.exec_command(command, timeout=timeout)
        stdout_text = stdout.read().decode("utf-8", errors="replace")
        stderr_text = stderr.read().decode("utf-8", errors="replace")
        exit_code = stdout.channel.recv_exit_status()
        if stdout_text:
            print(stdout_text, end="")
        if exit_code != 0:
            raise PipelineError(f"Polecenie SSH zakończyło się kodem {exit_code}: {stderr_text.strip()}")
    except paramiko.AuthenticationException as error:
        raise PipelineError("Błąd uwierzytelniania SSH") from error
    except paramiko.BadHostKeyException as error:
        raise PipelineError("Niepoprawny klucz hosta SSH") from error
    except paramiko.SSHException as error:
        raise PipelineError(f"Błąd SSH: {error}") from error
    except OSError as error:
        raise PipelineError(f"Nie można połączyć się przez SSH: {error}") from error
    finally:
        client.close()


def check_health(url: str, timeout: int) -> None:
    if requests is None:
        raise PipelineError("Brak requests. Zainstaluj pakiet: pip install requests")
    try:
        response = requests.get(url, timeout=timeout)
    except requests.RequestException as error:
        raise PipelineError(f"Health check nieudany: {error}") from error
    if response.status_code != 200:
        raise PipelineError(f"Health check zwrócił HTTP {response.status_code}")


def deploy_pipeline(args: argparse.Namespace) -> None:
    print("1/7 Pobieranie repozytorium Git...")
    update_repository(args.repo_url, args.repo_dir, args.branch, args.timeout)
    print("2/7 Uruchamianie testów pytest...")
    run_command([sys.executable, "-m", "pytest"], args.repo_dir, args.timeout)
    print("3/7 Budowanie obrazu Docker...")
    local_image, tag = build_image(args.repo_dir, args.image, args.timeout)
    print("4/7 Wysyłanie obrazu do ECR...")
    remote_image = push_to_ecr(local_image, args.ecr_repository, args.region, tag, args.timeout)
    print(f"Wysłano: {remote_image}")
    print("5/7 Deployment na EC2 przez SSH...")
    run_ssh_command(args.host, args.username, args.key_path, args.deploy_command, args.timeout, args.known_hosts)
    print("6/7 Health check...")
    try:
        check_health(args.health_url, args.timeout)
    except PipelineError as health_error:
        print("7/7 Health check nieudany, uruchamiam rollback...")
        try:
            run_ssh_command(
                args.host,
                args.username,
                args.key_path,
                args.rollback_command,
                args.timeout,
                args.known_hosts,
            )
        except PipelineError as rollback_error:
            raise PipelineError(f"{health_error}; rollback nieudany: {rollback_error}") from rollback_error
        raise health_error
    print("7/7 Health check poprawny - rollback nie jest potrzebny.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pipeline: Git, pytest, Docker, ECR, SSH i health check.")
    parser.add_argument("--repo-url", required=True)
    parser.add_argument("--repo-dir", type=Path, required=True)
    parser.add_argument("--branch", default="main")
    parser.add_argument("--image", required=True, help="Np. moja-aplikacja:latest")
    parser.add_argument("--ecr-repository", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--key-path", type=Path, required=True)
    parser.add_argument("--known-hosts", type=Path)
    parser.add_argument("--deploy-command", required=True)
    parser.add_argument("--rollback-command", required=True)
    parser.add_argument("--health-url", required=True)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--execute", action="store_true", help="Potwierdza wykonanie deploymentu.")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout musi być dodatni")
    if not args.execute:
        parser.error("Dodaj --execute, aby wykonać deployment")
    return args


def main() -> int:
    args = parse_args()
    try:
        deploy_pipeline(args)
    except PipelineError as error:
        print(f"Błąd pipeline: {error}", file=sys.stderr)
        return 1
    print("Deployment zakończony pomyślnie.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
