import asyncio
import random


async def dlugie_obliczenia():
    await asyncio.sleep(random.uniform(2, 5))
    return random.randint(1, 100)


async def main():
    wyniki = await asyncio.gather(*(dlugie_obliczenia() for _ in range(10)))
    print(f"Wyniki: {wyniki}")
    print(f"Suma wyników: {sum(wyniki)}")


if __name__ == "__main__":
    asyncio.run(main())
