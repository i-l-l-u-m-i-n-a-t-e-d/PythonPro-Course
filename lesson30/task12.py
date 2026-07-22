import asyncio
import random


async def zadanie(numer):
    czas_usypiania = random.uniform(1, 10)
    await asyncio.sleep(czas_usypiania)
    return numer, czas_usypiania


async def main():
    zadania = [asyncio.create_task(zadanie(numer)) for numer in range(1, 6)]
    zakonczone, oczekujace = await asyncio.wait(
        zadania, return_when=asyncio.FIRST_COMPLETED
    )

    pierwsze = next(iter(zakonczone))
    numer, czas = pierwsze.result()
    print(f"Pierwsze zakończone zadanie: {numer}, czas: {czas:.2f} s")

    for task in oczekujace:
        task.cancel()
    await asyncio.gather(*oczekujace, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
