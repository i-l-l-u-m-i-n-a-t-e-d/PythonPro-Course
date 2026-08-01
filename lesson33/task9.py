# .private/tasks_8_14/task9.py
from aiohttp import web


async def broadcast(clients: set[web.WebSocketResponse], text: str) -> None:
    for client in tuple(clients):
        if client.closed:
            clients.discard(client)
            continue
        try:
            await client.send_str(text)
        except Exception:
            clients.discard(client)


async def chat_handler(request: web.Request) -> web.WebSocketResponse:
    clients: set[web.WebSocketResponse] = request.app["clients"]
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    clients.add(ws)
    nickname: str | None = None

    try:
        async for message in ws:
            if message.type == web.WSMsgType.TEXT:
                if nickname is None:
                    nickname = message.data.strip()
                    if not nickname or len(nickname) > 32:
                        await ws.close(code=1008, message=b"Invalid nickname")
                        break
                else:
                    await broadcast(clients, f"{nickname}: {message.data}")
            elif message.type == web.WSMsgType.ERROR:
                break
    finally:
        clients.discard(ws)

    return ws


def create_app() -> web.Application:
    app = web.Application()
    app["clients"] = set()
    app.router.add_get("/chat", chat_handler)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="localhost", port=8080)
