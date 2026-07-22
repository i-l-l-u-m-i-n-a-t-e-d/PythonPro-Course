import asyncio
import json

import aiohttp

ORIGINAL_URL = "https://api.coindesk.com/v1/bpi/currentprice.json"

FALLBACK_URL = "https://api.coinbase.com/v2/prices/BTC-USD/spot"


async def coindesk_price(session: aiohttp.ClientSession) -> str:
    async with session.get(ORIGINAL_URL) as response:
        response.raise_for_status()
        data = await response.json()
    return data["bpi"]["USD"]["rate"]


async def coinbase_price(session: aiohttp.ClientSession) -> str:
    async with session.get(FALLBACK_URL) as response:
        response.raise_for_status()
        data = await response.json()
    return data["data"]["amount"]


async def main() -> None:
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            price = await coindesk_price(session)
            source = ORIGINAL_URL
        except (aiohttp.ClientError, asyncio.TimeoutError, KeyError, ValueError, json.JSONDecodeError):
            price = await coinbase_price(session)
            source = FALLBACK_URL
    print(f"Cena Bitcoina w USD ({source}): {price}")


if __name__ == "__main__":
    asyncio.run(main())
