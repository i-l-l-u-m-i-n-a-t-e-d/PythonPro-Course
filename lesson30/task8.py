import asyncio
import random


async def ping(host):
    await asyncio.sleep(random.uniform(0.1, 1.0))
    return f"Host {host} odpowiada"


async def main():
    hosty = ["serwer1", "serwer2", "serwer3", "serwer4", "serwer5"]
    wyniki = await asyncio.gather(*(ping(host) for host in hosty))

    for wynik in wyniki:
        print(wynik)


if __name__ == "__main__":
    asyncio.run(main())
