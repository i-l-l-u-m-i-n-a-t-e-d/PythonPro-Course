# .private/tasks_15_20/task18.py
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any

import jwt
from aiohttp import WSCloseCode, WSMsgType, web


@dataclass(frozen=True)
class Notification:
    recipient_id: str
    text: str
    sender_id: str

    def as_dict(self) -> dict[str, str]:
        return {
            "recipient_id": self.recipient_id,
            "text": self.text,
            "sender_id": self.sender_id,
        }


def decode_token(token: str, secret: str) -> str | None:
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
    except jwt.InvalidTokenError:
        return None
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        return None
    return subject


def token_from_authorization(request: web.Request) -> str | None:
    value = request.headers.get("Authorization", "")
    scheme, _, token = value.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


class NotificationHub:
    def __init__(self) -> None:
        self._connections: dict[str, set[web.WebSocketResponse]] = {}
        self._lock = asyncio.Lock()

    async def add(self, user_id: str, ws: web.WebSocketResponse) -> None:
        async with self._lock:
            self._connections.setdefault(user_id, set()).add(ws)

    async def remove(self, user_id: str, ws: web.WebSocketResponse) -> None:
        async with self._lock:
            sockets = self._connections.get(user_id)
            if sockets is None:
                return
            sockets.discard(ws)
            if not sockets:
                self._connections.pop(user_id, None)

    async def deliver(self, notification: Notification) -> None:
        async with self._lock:
            sockets = tuple(self._connections.get(notification.recipient_id, set()))

        stale: list[web.WebSocketResponse] = []
        for ws in sockets:
            if ws.closed:
                stale.append(ws)
                continue
            try:
                await ws.send_json({"type": "notification", **notification.as_dict()})
            except Exception:
                stale.append(ws)

        for ws in stale:
            await self.remove(notification.recipient_id, ws)

    async def close(self) -> None:
        async with self._lock:
            sockets = tuple(
                socket
                for user_sockets in self._connections.values()
                for socket in user_sockets
            )
            self._connections.clear()
        for socket in sockets:
            if not socket.closed:
                await socket.close()


def authenticated_user(request: web.Request) -> str:
    token = token_from_authorization(request)
    user_id = decode_token(token, request.app["jwt_secret"]) if token else None
    if user_id is None:
        raise web.HTTPUnauthorized(text="Nieprawidłowy token")
    return user_id


async def create_notification(request: web.Request) -> web.Response:
    sender_id = authenticated_user(request)
    try:
        data = await request.json()
    except (json.JSONDecodeError, ValueError):
        raise web.HTTPBadRequest(text="Niepoprawny JSON") from None

    recipient_id = data.get("recipient_id") if isinstance(data, dict) else None
    text = data.get("text") if isinstance(data, dict) else None
    if (
        not isinstance(recipient_id, str)
        or not isinstance(text, str)
    ):
        raise web.HTTPBadRequest(text="Niepoprawne powiadomienie")

    recipient_id = recipient_id.strip()
    if (
        not recipient_id
        or len(recipient_id) > 100
        or not text.strip()
        or len(text) > 1000
    ):
        raise web.HTTPBadRequest(text="Niepoprawne powiadomienie")

    notification = Notification(
        recipient_id=recipient_id,
        text=text,
        sender_id=sender_id,
    )
    await request.app["hub"].deliver(notification)
    return web.json_response(notification.as_dict(), status=201)


async def notification_websocket(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    try:
        first_message = await ws.receive(timeout=request.app["authentication_timeout"])
    except asyncio.TimeoutError:
        await ws.close(code=WSCloseCode.POLICY_VIOLATION)
        return ws
    if first_message.type != WSMsgType.TEXT:
        await ws.close(code=WSCloseCode.POLICY_VIOLATION)
        return ws
    try:
        payload = json.loads(first_message.data)
        token = payload["token"] if isinstance(payload, dict) else None
    except (json.JSONDecodeError, KeyError, TypeError):
        token = None

    user_id = (
        decode_token(token, request.app["jwt_secret"])
        if isinstance(token, str)
        else None
    )
    if user_id is None:
        await ws.send_json({"type": "error", "message": "Nieprawidłowy token"})
        await ws.close(code=WSCloseCode.POLICY_VIOLATION)
        return ws

    hub: NotificationHub = request.app["hub"]
    await hub.add(user_id, ws)
    await ws.send_json({"type": "authenticated", "user_id": user_id})
    try:
        async for message in ws:
            if message.type == WSMsgType.ERROR:
                break
    finally:
        await hub.remove(user_id, ws)
    return ws


async def on_cleanup(app: web.Application) -> None:
    await app["hub"].close()


def create_app(
    jwt_secret: str | None = None, authentication_timeout: float = 5
) -> web.Application:
    secret = jwt_secret or os.environ.get("JWT_SECRET")
    if not secret:
        raise RuntimeError("Ustaw zmienną środowiskową JWT_SECRET")

    app = web.Application()
    app["jwt_secret"] = secret
    app["authentication_timeout"] = authentication_timeout
    app["hub"] = NotificationHub()
    app.router.add_post("/notifications", create_notification)
    app.router.add_get("/ws/notifications", notification_websocket)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="127.0.0.1", port=8080)

