import asyncio
import json

import aiohttp

ORIGINAL_URL = "https://api.publicapis.org/random?auth=null"

FALLBACK_URLS = [
    "https://jsonplaceholder.typicode.com/todos/1",
    "https://jsonplaceholder.typicode.com/todos/2",
    "https://jsonplaceholder.typicode.com/todos/3",
]


async def fetch(session: aiohttp.ClientSession, url: str) -> dict:
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.json()


async def download_all(
    session: aiohttp.ClientSession, urls: list[str]
) -> list[dict | BaseException]:
    return await asyncio.gather(
        *(fetch(session, url) for url in urls), return_exceptions=True
    )


async def main() -> None:
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        urls = [ORIGINAL_URL, ORIGINAL_URL, ORIGINAL_URL]
        results = await download_all(session, urls)
        if all(isinstance(result, BaseException) for result in results):
            urls = FALLBACK_URLS
            results = await download_all(session, urls)

    for url, result in zip(urls, results, strict=True):
        if isinstance(result, BaseException):
            print(f"{url}: błąd {type(result).__name__}: {result}")
        else:
            print(f"{url}: {json.dumps(result, ensure_ascii=False)}")


if __name__ == "__main__":
    asyncio.run(main())
