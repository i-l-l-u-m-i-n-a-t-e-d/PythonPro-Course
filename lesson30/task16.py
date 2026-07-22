import asyncio
import time


class RateLimiter:
    def __init__(self, limit_na_sekunde):
        self.odstep = 1 / limit_na_sekunde
        self.nastepny_dozwolony_czas = 0.0
        self.blokada = asyncio.Lock()

    async def acquire(self):
        petla = asyncio.get_running_loop()
        async with self.blokada:
            teraz = petla.time()
            dozwolony_czas = max(teraz, self.nastepny_dozwolony_czas)
            self.nastepny_dozwolony_czas = dozwolony_czas + self.odstep

        czas_czekania = dozwolony_czas - teraz
        if czas_czekania > 0:
            await asyncio.sleep(czas_czekania)


async def wykonaj_zadanie(numer, ogranicznik, start):
    await ogranicznik.acquire()
    czas = time.perf_counter() - start
    print(f"Zadanie {numer}: dozwolone po {czas:.2f} s")


async def main():
    ogranicznik = RateLimiter(5)
    start = time.perf_counter()
    await asyncio.gather(
        *(wykonaj_zadanie(numer, ogranicznik, start) for numer in range(1, 21))
    )


if __name__ == "__main__":
    asyncio.run(main())
