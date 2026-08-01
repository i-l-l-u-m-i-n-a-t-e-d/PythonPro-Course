# .private/tasks_8_14/task14.py
import os

from aiohttp import web
import jwt


JWT_ALGORITHM = "HS256"
AUTH_TIMEOUT = 30


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    try:
        first_message = await ws.receive(timeout=request.app["auth_timeout"])
    except TimeoutError:
        await ws.close(code=1008, message=b"JWT timeout")
        return ws
    if first_message.type != web.WSMsgType.TEXT:
        await ws.close(code=1008, message=b"JWT required")
        return ws

    try:
        jwt.decode(
            first_message.data,
            request.app["jwt_secret"],
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp"]},
        )
    except jwt.InvalidTokenError:
        await ws.close(code=1008, message=b"Invalid JWT")
        return ws

    await ws.send_str("Authenticated")
    async for message in ws:
        if message.type == web.WSMsgType.TEXT:
            await ws.send_str(f"Accepted: {message.data}")
        elif message.type == web.WSMsgType.ERROR:
            break

    return ws


def create_app(auth_timeout: float = AUTH_TIMEOUT) -> web.Application:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("Set JWT_SECRET before starting the server")

    app = web.Application()
    app["jwt_secret"] = secret
    app["auth_timeout"] = auth_timeout
    app.router.add_get("/ws", websocket_handler)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="localhost", port=8080)
