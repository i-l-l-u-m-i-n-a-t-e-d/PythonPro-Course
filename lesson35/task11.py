"""Route53 weighted routing 80/20 i test bez cache lokalnego DNS."""

from __future__ import annotations

import argparse
import http.client
import secrets
import socket
import struct
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


PRIMARY_WEIGHT = 80
CANARY_WEIGHT = 20
REQUEST_COUNT = 100
PRIMARY_ACCEPTABLE_MIN = 70
PRIMARY_ACCEPTABLE_MAX = 90


def make_route53_client(profile: str | None) -> Any:
    try:
        import boto3
    except ImportError as error:
        raise RuntimeError("Brakuje boto3. Zainstaluj je w używanym środowisku.") from error

    return boto3.Session(profile_name=profile).client("route53")


def normalize_record_name(name: str) -> str:
    normalized = name.strip().rstrip(".")
    if not normalized or "." not in normalized or any(part == "" for part in normalized.split(".")):
        raise ValueError("--record-name musi być pełną nazwą DNS, np. app.example.com.")
    return f"{normalized}."


def normalize_zone_id(value: str, option: str) -> str:
    normalized = value.strip().rstrip("/").split("/")[-1]
    if not normalized:
        raise ValueError(f"{option} nie może być puste.")
    return normalized


def normalize_dns_name(value: str, option: str) -> str:
    name = value.strip().rstrip(".")
    if not name:
        raise ValueError(f"{option} nie może być pusty.")
    return f"{name}."


def alias_target(dns_name: str, hosted_zone_id: str) -> dict[str, Any]:
    return {
        "HostedZoneId": normalize_zone_id(hosted_zone_id, "HostedZoneId"),
        "DNSName": normalize_dns_name(dns_name, "DNS endpointu"),
        "EvaluateTargetHealth": True,
    }


def configure_weighted_routing(
    client: Any,
    *,
    hosted_zone_id: str,
    record_name: str,
    primary_dns_name: str,
    primary_zone_id: str,
    canary_dns_name: str,
    canary_zone_id: str,
    waiter_delay: int,
    waiter_attempts: int,
) -> str:
    """Tworzy idempotentne rekordy alias A o wagach 80 oraz 20."""
    response = client.change_resource_record_sets(
        HostedZoneId=normalize_zone_id(hosted_zone_id, "--hosted-zone-id"),
        ChangeBatch={
            "Comment": "Lesson 36 weighted routing 80/20",
            "Changes": [
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": record_name,
                        "Type": "A",
                        "SetIdentifier": "primary",
                        "Weight": PRIMARY_WEIGHT,
                        "AliasTarget": alias_target(primary_dns_name, primary_zone_id),
                    },
                },
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": record_name,
                        "Type": "A",
                        "SetIdentifier": "canary",
                        "Weight": CANARY_WEIGHT,
                        "AliasTarget": alias_target(canary_dns_name, canary_zone_id),
                    },
                },
            ],
        },
    )
    change_id = response["ChangeInfo"]["Id"]
    client.get_waiter("resource_record_sets_changed").wait(
        Id=change_id,
        WaiterConfig={"Delay": waiter_delay, "MaxAttempts": waiter_attempts},
    )
    return change_id


def encode_dns_name(name: str) -> bytes:
    labels = name.rstrip(".").split(".")
    if not labels or any(not label for label in labels):
        raise ValueError("Nieprawidłowa nazwa DNS.")
    encoded = bytearray()
    for label in labels:
        label_bytes = label.encode("idna")
        if len(label_bytes) > 63:
            raise ValueError("Etykieta DNS jest zbyt długa.")
        encoded.append(len(label_bytes))
        encoded.extend(label_bytes)
    encoded.append(0)
    return bytes(encoded)


def skip_dns_name(packet: bytes, offset: int) -> int:
    while True:
        if offset >= len(packet):
            raise RuntimeError("Skrócona odpowiedź DNS.")
        length = packet[offset]
        if length == 0:
            return offset + 1
        if length & 0xC0 == 0xC0:
            if offset + 1 >= len(packet):
                raise RuntimeError("Skrócona kompresja nazwy DNS.")
            return offset + 2
        if length & 0xC0 or offset + length >= len(packet):
            raise RuntimeError("Nieprawidłowa nazwa w odpowiedzi DNS.")
        offset += length + 1


def query_authoritative_a(name_server: str, record_name: str, timeout: int) -> list[str]:
    """Pyta bezpośrednio autorytatywny Route53 NS, bez cache rekurencyjnego resolvera."""
    query_id = secrets.randbelow(65_536)
    query = struct.pack("!HHHHHH", query_id, 0, 1, 0, 0, 0)
    query += encode_dns_name(record_name) + struct.pack("!HH", 1, 1)
    server = name_server.rstrip(".")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            udp.settimeout(timeout)
            udp.sendto(query, (server, 53))
            packet, _address = udp.recvfrom(4096)
    except OSError as error:
        raise RuntimeError(f"Zapytanie do autorytatywnego DNS {server} nie powiodło się: {error}") from error

    if len(packet) < 12:
        raise RuntimeError("Skrócona odpowiedź DNS.")
    response_id, flags, question_count, answer_count, _authority, _additional = struct.unpack("!HHHHHH", packet[:12])
    if response_id != query_id or not flags & 0x8000:
        raise RuntimeError("Nieprawidłowa odpowiedź od autorytatywnego DNS.")
    if flags & 0x0200:
        raise RuntimeError("Odpowiedź DNS jest skrócona; użyj dostępnego DNS bez truncation.")
    response_code = flags & 0x000F
    if response_code:
        raise RuntimeError(f"Autorytatywny DNS zwrócił kod błędu {response_code}.")

    offset = 12
    for _ in range(question_count):
        offset = skip_dns_name(packet, offset)
        if offset + 4 > len(packet):
            raise RuntimeError("Skrócone pytanie DNS.")
        offset += 4
    addresses: list[str] = []
    for _ in range(answer_count):
        offset = skip_dns_name(packet, offset)
        if offset + 10 > len(packet):
            raise RuntimeError("Skrócona odpowiedź DNS.")
        record_type, record_class, _ttl, length = struct.unpack("!HHIH", packet[offset : offset + 10])
        offset += 10
        if offset + length > len(packet):
            raise RuntimeError("Skrócone dane odpowiedzi DNS.")
        data = packet[offset : offset + length]
        offset += length
        if record_type == 1 and record_class == 1 and length == 4:
            addresses.append(socket.inet_ntoa(data))
    if not addresses:
        raise RuntimeError("Autorytatywny DNS nie zwrócił rekordu A dla weighted record.")
    return addresses


def authoritative_name_servers(client: Any, hosted_zone_id: str) -> list[str]:
    response = client.get_hosted_zone(Id=normalize_zone_id(hosted_zone_id, "--hosted-zone-id"))
    name_servers = response.get("DelegationSet", {}).get("NameServers", [])
    if not name_servers:
        raise RuntimeError("Hosted Zone nie zwróciła autorytatywnych Name Servers.")
    return name_servers


def endpoint_addresses(dns_name: str) -> set[str]:
    host = dns_name.rstrip(".")
    try:
        records = socket.getaddrinfo(host, 80, family=socket.AF_INET, type=socket.SOCK_STREAM)
    except OSError as error:
        raise RuntimeError(f"Nie można rozwiązać endpointu {host}: {error}") from error
    addresses = {record[4][0] for record in records}
    if not addresses:
        raise RuntimeError(f"Endpoint {host} nie zwrócił adresów IPv4.")
    return addresses


def endpoint_ip_map(primary_dns_name: str, canary_dns_name: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for label, endpoint in (("primary", primary_dns_name), ("canary", canary_dns_name)):
        for address in endpoint_addresses(endpoint):
            previous = mapping.get(address)
            if previous is not None and previous != label:
                raise RuntimeError("Primary i canary mają wspólny adres IP; nie można rzetelnie rozpoznać endpointu.")
            mapping[address] = label
    return mapping


def probe_path(path: str, token: str, number: int) -> str:
    separator = "&" if "?" in path else "?"
    return f"{path}{separator}weighted_probe={token}-{number}"


def direct_http_request(address: str, host_header: str, path: str, timeout: int) -> None:
    """Łączy się z IP wskazanym przez Route53, zachowując Host weighted record."""
    connection = http.client.HTTPConnection(address, 80, timeout=timeout)
    try:
        connection.request(
            "GET",
            path,
            headers={"Host": host_header, "Connection": "close", "Cache-Control": "no-cache"},
        )
        response = connection.getresponse()
        response.read()
        if not 200 <= response.status < 400:
            raise RuntimeError(f"HTTP {response.status}")
    except OSError as error:
        raise RuntimeError(f"Żądanie HTTP do {address} nie powiodło się: {error}") from error
    finally:
        connection.close()


def resolved_endpoint(
    record_name: str,
    name_servers: list[str],
    ip_map: dict[str, str],
    dns_timeout: int,
) -> tuple[str, str]:
    name_server = secrets.choice(name_servers)
    addresses = query_authoritative_a(name_server, record_name, dns_timeout)
    mapped = [(address, ip_map[address]) for address in addresses if address in ip_map]
    labels = {label for _address, label in mapped}
    if len(labels) != 1:
        raise RuntimeError("Odpowiedź Route53 nie daje się przypisać jednoznacznie do primary albo canary.")
    address, label = secrets.choice(mapped)
    return address, label


def test_weighted_routing(
    record_name: str,
    *,
    primary_dns_name: str,
    canary_dns_name: str,
    name_servers: list[str],
    path: str = "/",
    request_timeout: int = 10,
    dns_timeout: int = 5,
) -> dict[str, int]:
    """Wysyła 100 żądań po 100 autorytatywnych zapytaniach DNS, bez lokalnego cache."""
    ip_map = endpoint_ip_map(primary_dns_name, canary_dns_name)
    counts = {"primary": 0, "canary": 0}
    token = secrets.token_hex(12)
    failures: list[str] = []
    for number in range(1, REQUEST_COUNT + 1):
        try:
            try:
                address, endpoint = resolved_endpoint(record_name, name_servers, ip_map, dns_timeout)
            except RuntimeError:
                ip_map = endpoint_ip_map(primary_dns_name, canary_dns_name)
                address, endpoint = resolved_endpoint(record_name, name_servers, ip_map, dns_timeout)
            direct_http_request(address, record_name.rstrip("."), probe_path(path, token, number), request_timeout)
            counts[endpoint] += 1
        except RuntimeError as error:
            failures.append(str(error))
    if failures:
        raise RuntimeError(f"Nieudane żądania: {len(failures)}/{REQUEST_COUNT}.")
    if not counts["primary"] or not counts["canary"]:
        raise RuntimeError("Test nie zaobserwował obu endpointów mimo bezpośrednich zapytań do DNS autorytatywnego.")
    return counts


def is_approximately_weighted(counts: dict[str, int]) -> bool:
    return PRIMARY_ACCEPTABLE_MIN <= counts["primary"] <= PRIMARY_ACCEPTABLE_MAX


def print_result(counts: dict[str, int]) -> None:
    print("Weryfikacja: 100 autorytatywnych odpowiedzi Route53 + bezpośrednie HTTP do zwróconego IP")
    print(f"primary: {counts['primary']} ({counts['primary']}%)")
    print(f"canary: {counts['canary']} ({counts['canary']}%)")
    print(
        "Wynik zbliżony do 80/20 "
        f"(primary {PRIMARY_ACCEPTABLE_MIN}-{PRIMARY_ACCEPTABLE_MAX}%): "
        f"{'tak' if is_approximately_weighted(counts) else 'nie'}"
    )


def require_expected_distribution(counts: dict[str, int]) -> None:
    if not is_approximately_weighted(counts):
        raise RuntimeError("Wynik 100 żądań nie jest wystarczająco zbliżony do oczekiwanych wag 80/20.")


def require_confirmation(args: argparse.Namespace) -> None:
    if not (args.apply and args.confirm):
        raise RuntimeError("Zmiana Route53 wymaga jednocześnie --apply --confirm.")


def required_test_values(args: argparse.Namespace) -> None:
    if not args.primary_dns_name or not args.canary_dns_name:
        raise ValueError("Test wymaga --primary-dns-name i --canary-dns-name do identyfikacji endpointów.")
    normalize_dns_name(args.primary_dns_name, "--primary-dns-name")
    normalize_dns_name(args.canary_dns_name, "--canary-dns-name")
    if not args.authoritative_ns and not args.hosted_zone_id:
        raise ValueError("Test wymaga --hosted-zone-id albo co najmniej jednego --authoritative-ns.")


def name_servers_for_test(client: Any, args: argparse.Namespace) -> list[str]:
    if args.authoritative_ns:
        return [normalize_dns_name(server, "--authoritative-ns") for server in args.authoritative_ns]
    return authoritative_name_servers(client, args.hosted_zone_id)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Weighted routing Route53 80% primary / 20% canary")
    parser.add_argument("--action", choices=("configure", "test"), required=True)
    parser.add_argument("--record-name", required=True, help="Pełna nazwa rekordu Route53")
    parser.add_argument("--profile", help="Opcjonalny profil AWS")
    parser.add_argument("--hosted-zone-id", help="Hosted Zone do configure lub odczytu Name Servers")
    parser.add_argument("--primary-dns-name", help="DNS primary ALB")
    parser.add_argument("--primary-zone-id", help="CanonicalHostedZoneId primary ALB")
    parser.add_argument("--canary-dns-name", help="DNS canary ALB")
    parser.add_argument("--canary-zone-id", help="CanonicalHostedZoneId canary ALB")
    parser.add_argument("--authoritative-ns", action="append", default=[], help="Opcjonalny autorytatywny NS Route53")
    parser.add_argument("--path", default="/")
    parser.add_argument("--request-timeout", type=int, default=10)
    parser.add_argument("--dns-timeout", type=int, default=5)
    parser.add_argument("--wait-delay", type=int, default=30)
    parser.add_argument("--wait-attempts", type=int, default=60)
    parser.add_argument("--apply", action="store_true", help="Zezwala na UPSERT rekordów Route53")
    parser.add_argument("--confirm", action="store_true", help="Potwierdza zmianę DNS")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        record_name = normalize_record_name(args.record_name)
        if not args.path.startswith("/") or args.request_timeout < 1 or args.dns_timeout < 1:
            raise ValueError("Ścieżka musi zaczynać się od '/', a timeouty być dodatnie.")
        if args.action == "test":
            required_test_values(args)
            client = make_route53_client(args.profile)
            counts = test_weighted_routing(
                record_name,
                primary_dns_name=args.primary_dns_name,
                canary_dns_name=args.canary_dns_name,
                name_servers=name_servers_for_test(client, args),
                path=args.path,
                request_timeout=args.request_timeout,
                dns_timeout=args.dns_timeout,
            )
            print_result(counts)
            require_expected_distribution(counts)
            return 0

        require_confirmation(args)
        if not all(
            (
                args.hosted_zone_id,
                args.primary_dns_name,
                args.primary_zone_id,
                args.canary_dns_name,
                args.canary_zone_id,
            )
        ):
            raise ValueError("Configure wymaga Hosted Zone oraz obu endpointów i ich CanonicalHostedZoneId.")
        if args.wait_delay < 1 or args.wait_attempts < 1:
            raise ValueError("Parametry waitera muszą być dodatnie.")
        client = make_route53_client(args.profile)
        change_id = configure_weighted_routing(
            client,
            hosted_zone_id=args.hosted_zone_id,
            record_name=record_name,
            primary_dns_name=args.primary_dns_name,
            primary_zone_id=args.primary_zone_id,
            canary_dns_name=args.canary_dns_name,
            canary_zone_id=args.canary_zone_id,
            waiter_delay=args.wait_delay,
            waiter_attempts=args.wait_attempts,
        )
        print(f"Zmiana Route53 jest INSYNC: {change_id}")
        counts = test_weighted_routing(
            record_name,
            primary_dns_name=args.primary_dns_name,
            canary_dns_name=args.canary_dns_name,
            name_servers=name_servers_for_test(client, args),
            path=args.path,
            request_timeout=args.request_timeout,
            dns_timeout=args.dns_timeout,
        )
        print_result(counts)
        require_expected_distribution(counts)
        return 0
    except (NoCredentialsError, PartialCredentialsError):
        print("Brak poprawnych poświadczeń AWS.")
        return 2
    except (ClientError, WaiterError, BotoCoreError, RuntimeError, ValueError) as error:
        print(f"Weighted routing/test nie został ukończony: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
