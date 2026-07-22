import asyncio
from pathlib import Path
from uuid import uuid4

try:
    import aiofiles
except ImportError:
    aiofiles = None


async def zapisz_log(numer, sciezka, blokada):
    await asyncio.sleep(0.1 * numer)
    wpis = f"Log z korutyny {numer}\n"

    async with blokada:
        async with aiofiles.open(sciezka, "a", encoding="utf-8") as plik:
            await plik.write(wpis)


async def main():
    if aiofiles is None:
        print("Brak biblioteki aiofiles. Zainstaluj ją poleceniem: pip install aiofiles")
        return

    blokada = asyncio.Lock()
    katalog_roboczy = Path(__file__).resolve().parent.parent
    sciezka = katalog_roboczy / f".task15_logi_{uuid4().hex}.txt"
    try:
        await asyncio.gather(
            *(zapisz_log(numer, sciezka, blokada) for numer in range(1, 6))
        )

        async with aiofiles.open(sciezka, "r", encoding="utf-8") as plik:
            print(await plik.read(), end="")
    finally:
        if sciezka.exists():
            sciezka.unlink()


if __name__ == "__main__":
    asyncio.run(main())
