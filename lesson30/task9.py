import asyncio

try:
    import aiohttp
except ImportError:
    aiohttp = None


async def sprawdz_status(session, url):
    try:
        async with session.get(url) as response:
            print(f"{url} - Status: {response.status}")
    except (aiohttp.ClientError, asyncio.TimeoutError) as blad:
        print(f"{url} - Błąd: {blad}")


async def main():
    if aiohttp is None:
        print("Brak biblioteki aiohttp. Zainstaluj ją poleceniem: pip install aiohttp")
        return

    adresy = [
        "https://www.google.com",
        "https://www.python.org",
        "https://httpbin.org/status/404",
    ]
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        await asyncio.gather(*(sprawdz_status(session, url) for url in adresy))


if __name__ == "__main__":
    asyncio.run(main())
