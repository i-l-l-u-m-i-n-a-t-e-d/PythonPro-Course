# .private/tasks_1_7/task7.py
from aiohttp import web


active_connections: set[web.WebSocketResponse] = set()


async def broadcast(message: str) -> None:
    for connection in tuple(active_connections):
        if connection.closed:
            active_connections.discard(connection)
            continue
        try:
            await connection.send_str(message)
        except (ConnectionResetError, RuntimeError):
            active_connections.discard(connection)


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    active_connections.add(ws)

    try:
        async for received in ws:
            if received.type == web.WSMsgType.TEXT:
                await broadcast(received.data)
    finally:
        active_connections.discard(ws)

    return ws


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/ws", websocket_handler)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="localhost", port=8080)
