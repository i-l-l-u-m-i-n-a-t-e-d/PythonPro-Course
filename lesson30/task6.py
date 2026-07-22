import asyncio


async def pobierz_pogode(miasto):
    await asyncio.sleep(1.5)
    return {"miasto": miasto, "temperatura": 25, "stan": "słonecznie"}


async def main():
    pogoda = await pobierz_pogode("Warszawa")
    print(pogoda)


if __name__ == "__main__":
    asyncio.run(main())
