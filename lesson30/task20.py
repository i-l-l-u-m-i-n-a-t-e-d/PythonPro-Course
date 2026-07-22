import asyncio
import random


async def losowe_zadanie(czas_snu):
    await asyncio.sleep(czas_snu)
    print("Zadanie zakończyło się przed limitem czasu.")


async def main():
    generator = random.Random(0)
    czas_snu = generator.uniform(1, 5)
    print(f"Zadanie będzie spało przez {czas_snu:.2f} s")

    try:
        await asyncio.wait_for(losowe_zadanie(czas_snu), timeout=3)
    except asyncio.TimeoutError:
        print("Przekroczono limit czasu 3 sekund.")


if __name__ == "__main__":
    asyncio.run(main())
