import asyncio


async def producent(kolejka):
    for liczba in range(1, 21):
        await asyncio.sleep(0.5)
        await kolejka.put(liczba)


async def konsument(numer, kolejka):
    while True:
        liczba = await kolejka.get()
        try:
            if liczba is None:
                return
            print(f"Konsument {numer} przetworzył liczbę: {liczba}")
        finally:
            kolejka.task_done()


async def main():
    kolejka = asyncio.Queue()
    konsumenci = [
        asyncio.create_task(konsument(1, kolejka)),
        asyncio.create_task(konsument(2, kolejka)),
    ]

    await producent(kolejka)
    await kolejka.join()

    for _ in konsumenci:
        await kolejka.put(None)
    await asyncio.gather(*konsumenci)


if __name__ == "__main__":
    asyncio.run(main())
