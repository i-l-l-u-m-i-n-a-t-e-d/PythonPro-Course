import asyncio


def czy_pierwsza(liczba):
    if liczba < 2:
        return False
    for dzielnik in range(2, int(liczba**0.5) + 1):
        if liczba % dzielnik == 0:
            return False
    return True


async def liczby_pierwsze():
    liczba = 2
    while True:
        if czy_pierwsza(liczba):
            await asyncio.sleep(0.1)
            yield liczba
        liczba += 1


async def main():
    async for liczba in liczby_pierwsze():
        if liczba > 100:
            break
        print(liczba)


if __name__ == "__main__":
    asyncio.run(main())
