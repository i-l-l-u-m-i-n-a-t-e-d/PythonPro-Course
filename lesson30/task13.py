import asyncio


async def obsluz_klienta(reader, writer):
    try:
        wiadomosc = await reader.read(1024)
        if wiadomosc:
            writer.write(wiadomosc)
            await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()


async def klient_testowy():
    reader, writer = await asyncio.open_connection("localhost", 8888)
    wiadomosc = "Wiadomość testowa".encode("utf-8")
    writer.write(wiadomosc)
    await writer.drain()

    odpowiedz = await reader.read(1024)
    print(f"Odpowiedź serwera: {odpowiedz.decode('utf-8')}")

    writer.close()
    await writer.wait_closed()


async def main():
    try:
        server = await asyncio.start_server(obsluz_klienta, "localhost", 8888)
    except OSError as blad:
        print(f"Nie można uruchomić serwera na localhost:8888: {blad}")
        return

    print("Serwer nasłuchuje na localhost:8888")
    try:
        await klient_testowy()
    finally:
        server.close()
        await server.wait_closed()
        print("Serwer zamknięty")


if __name__ == "__main__":
    asyncio.run(main())
