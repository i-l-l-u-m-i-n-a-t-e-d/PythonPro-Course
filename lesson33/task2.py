# .private/tasks_1_7/task2.py
import asyncio

import aiohttp


MESSAGES = ("Cześć", "Jak się masz?", "Do widzenia")


async def websocket_client(url: str = "ws://localhost:8080/ws") -> None:
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(url) as ws:
            for message in MESSAGES:
                await ws.send_str(message)
                await ws.receive()


if __name__ == "__main__":
    asyncio.run(websocket_client())
