import asyncio


async def pierwsza_korutyna():
    print("Gotowy do nauki asyncio!")


if __name__ == "__main__":
    asyncio.run(pierwsza_korutyna())
