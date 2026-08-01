# .private/tasks_1_7/task1.py
from aiohttp import web


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async for message in ws:
        if message.type == web.WSMsgType.TEXT:
            await ws.send_str(f"Server: {message.data}")

    return ws


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/ws", websocket_handler)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="localhost", port=8080)
