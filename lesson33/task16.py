# .private/tasks_15_20/task16.py
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiosqlite
from aiohttp import WSMsgType, web


@dataclass(frozen=True)
class ChatMessage:
    id: int
    text: str

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "text": self.text}


class ChatStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        self._db: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def open(self) -> None:
        self._db = await aiosqlite.connect(self.database_path)
        await self._db.execute(
            "CREATE TABLE IF NOT EXISTS messages "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL)"
        )
        await self._db.commit()

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None

    async def add(self, text: str) -> ChatMessage:
        if self._db is None:
            raise RuntimeError("Baza danych nie jest otwarta")
        async with self._lock:
            cursor = await self._db.execute(
                "INSERT INTO messages(text) VALUES (?)", (text,)
            )
            await self._db.commit()
            message_id = int(cursor.lastrowid)
            await cursor.close()
        return ChatMessage(id=message_id, text=text)

    async def last_messages(self, limit: int = 50) -> list[ChatMessage]:
        if self._db is None:
            raise RuntimeError("Baza danych nie jest otwarta")
        async with self._lock:
            cursor = await self._db.execute(
                "SELECT id, text FROM messages ORDER BY id DESC LIMIT ?", (limit,)
            )
            rows = await cursor.fetchall()
            await cursor.close()
        return [ChatMessage(id=row[0], text=row[1]) for row in reversed(rows)]


class ChatServer:
    def __init__(self, store: ChatStore) -> None:
        self.store = store
        self.clients: set[web.WebSocketResponse] = set()
        self._lock = asyncio.Lock()

    async def _broadcast_locked(self, payload: dict[str, Any]) -> None:
        stale: set[web.WebSocketResponse] = set()
        for client in tuple(self.clients):
            if client.closed:
                stale.add(client)
                continue
            try:
                await client.send_json(payload)
            except Exception:
                stale.add(client)
        self.clients.difference_update(stale)

    async def handler(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        async with self._lock:
            history = await self.store.last_messages()
            self.clients.add(ws)
            await ws.send_json(
                {"type": "history", "messages": [item.as_dict() for item in history]}
            )

        try:
            async for message in ws:
                if message.type == WSMsgType.TEXT:
                    text = message.data.strip()
                    if not text or len(text) > 1000:
                        await ws.send_json({"type": "error", "message": "Niepoprawna wiadomość"})
                        continue
                    async with self._lock:
                        saved = await self.store.add(text)
                        await self._broadcast_locked(
                            {"type": "message", "message": saved.as_dict()}
                        )
                elif message.type == WSMsgType.ERROR:
                    break
        finally:
            async with self._lock:
                self.clients.discard(ws)
        return ws

    async def close(self) -> None:
        async with self._lock:
            clients = tuple(self.clients)
            self.clients.clear()
        for client in clients:
            if not client.closed:
                await client.close()


async def chat_handler(request: web.Request) -> web.WebSocketResponse:
    return await request.app["chat"].handler(request)


async def on_startup(app: web.Application) -> None:
    await app["chat"].store.open()


async def on_cleanup(app: web.Application) -> None:
    await app["chat"].close()
    await app["chat"].store.close()


def create_app(database_path: str | Path) -> web.Application:
    app = web.Application()
    app["chat"] = ChatServer(ChatStore(database_path))
    app.router.add_get("/chat", chat_handler)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__ == "__main__":
    web.run_app(create_app("chat_history.sqlite3"), host="127.0.0.1", port=8080)

