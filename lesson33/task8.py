# .private/tasks_8_14/task8.py
from aiohttp import web
import time


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    connected_at = time.monotonic()

    try:
        async for message in ws:
            if message.type == web.WSMsgType.ERROR:
                break
    finally:
        duration = time.monotonic() - connected_at
        print(f"Czas połączenia klienta: {duration:.2f} s")

    return ws


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/ws", websocket_handler)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="localhost", port=8080)
