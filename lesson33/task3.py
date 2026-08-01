# .private/tasks_1_7/task3.py
from aiohttp import web


active_connections: set[web.WebSocketResponse] = set()


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    active_connections.add(ws)

    try:
        await ws.send_str(f"Jesteś klientem numer {len(active_connections)}")
        async for message in ws:
            if message.type == web.WSMsgType.TEXT:
                await ws.send_str(f"Server: {message.data}")
    finally:
        active_connections.discard(ws)

    return ws


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/ws", websocket_handler)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="localhost", port=8080)
