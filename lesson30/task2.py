import asyncio


async def licznik(n):
    for liczba in range(1, n + 1):
        await asyncio.sleep(1)
        print(liczba)


async def main():
    await licznik(5)


if __name__ == "__main__":
    asyncio.run(main())
