# .private/tasks_8_14/task13.py
from aiohttp import web


def remove_from_room(
    rooms: dict[str, set[web.WebSocketResponse]],
    room_name: str,
    ws: web.WebSocketResponse,
) -> None:
    clients = rooms.get(room_name)
    if clients is None:
        return
    clients.discard(ws)
    if not clients:
        rooms.pop(room_name, None)


async def broadcast(
    rooms: dict[str, set[web.WebSocketResponse]], room_name: str, text: str
) -> None:
    clients = rooms.get(room_name, set())
    for client in tuple(clients):
        if client.closed:
            clients.discard(client)
            continue
        try:
            await client.send_str(text)
        except Exception:
            clients.discard(client)
    if not clients:
        rooms.pop(room_name, None)


async def chat_handler(request: web.Request) -> web.WebSocketResponse:
    rooms: dict[str, set[web.WebSocketResponse]] = request.app["rooms"]
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    room_name: str | None = None

    try:
        async for message in ws:
            if message.type != web.WSMsgType.TEXT:
                if message.type == web.WSMsgType.ERROR:
                    break
                continue

            text = message.data
            if text == "/join" or text.startswith("/join "):
                parts = text.split()
                if len(parts) != 2 or len(parts[1]) > 32:
                    await ws.send_str("Nieprawidłowy pokój")
                    continue
                new_room = parts[1]
                if room_name is not None:
                    remove_from_room(rooms, room_name, ws)
                rooms.setdefault(new_room, set()).add(ws)
                room_name = new_room
            elif room_name is None:
                await ws.send_str("Najpierw dołącz do pokoju")
            else:
                await broadcast(rooms, room_name, text)
    finally:
        if room_name is not None:
            remove_from_room(rooms, room_name, ws)

    return ws


def create_app() -> web.Application:
    app = web.Application()
    app["rooms"] = {}
    app.router.add_get("/chat", chat_handler)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="localhost", port=8080)
