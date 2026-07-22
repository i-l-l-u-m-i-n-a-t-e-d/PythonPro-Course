import asyncio
import time


async def simulated_task(delay: int) -> None:
    await asyncio.sleep(delay)


async def main() -> None:
    start = time.perf_counter()
    await asyncio.gather(
        simulated_task(1),
        simulated_task(4),
        simulated_task(2),
    )
    print(f"Całkowity czas wykonania: {time.perf_counter() - start:.2f} s")


if __name__ == "__main__":
    asyncio.run(main())
