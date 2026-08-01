from time import perf_counter

try:
    import requests
except ImportError:
    raise SystemExit(
        "Brak pakietu requests. Zainstaluj go: python -m pip install requests"
    )


SITES = (
    "https://example.com",
    "https://www.python.org",
    "https://httpbin.org/status/200",
)


def check_site(url: str) -> None:
    start = perf_counter()
    try:
        response = requests.get(url, timeout=5)
    except requests.RequestException as error:
        elapsed = perf_counter() - start
        print(f"{url}: BŁĄD ({error.__class__.__name__}, {elapsed:.2f} s)")
        return

    elapsed = perf_counter() - start
    if response.status_code == 200:
        status = "200 OK"
    else:
        status = f"status {response.status_code}"
    print(f"{url}: {status} (czas odpowiedzi: {elapsed:.2f} s)")


def main() -> None:
    for url in SITES:
        check_site(url)


if __name__ == "__main__":
    main()
