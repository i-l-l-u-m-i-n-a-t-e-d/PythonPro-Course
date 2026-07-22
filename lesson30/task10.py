import asyncio


async def odliczanie(nazwa, start):
    for pozostalo in range(start, 0, -1):
        print(f"{nazwa}: zostało {pozostalo} sekund")
        await asyncio.sleep(1)


async def main():
    await asyncio.gather(
        odliczanie("Odliczanie A", 5),
        odliczanie("Odliczanie B", 3),
        odliczanie("Odliczanie C", 7),
    )


if __name__ == "__main__":
    asyncio.run(main())
