# .private/tasks_15_20/task19.py
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import aiosqlite
import strawberry
from aiohttp import web
from strawberry.aiohttp.views import GraphQLView
from strawberry.subscriptions import GRAPHQL_TRANSPORT_WS_PROTOCOL


@strawberry.type
class UserProfile:
    id: strawberry.ID
    name: str
    email: str


@strawberry.type
class ChatMessage:
    id: strawberry.ID
    user_id: strawberry.ID
    text: str


class ChatStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        self._db: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def open(self) -> None:
        self._db = await aiosqlite.connect(self.database_path)
        await self._db.execute(
            "CREATE TABLE IF NOT EXISTS chat_messages ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, text TEXT NOT NULL)"
        )
        await self._db.commit()

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None

    async def add(self, user_id: str, text: str) -> ChatMessage:
        if self._db is None:
            raise RuntimeError("Baza danych nie jest otwarta")
        async with self._lock:
            cursor = await self._db.execute(
                "INSERT INTO chat_messages(user_id, text) VALUES (?, ?)",
                (user_id, text),
            )
            await self._db.commit()
            message_id = int(cursor.lastrowid)
            await cursor.close()
        return ChatMessage(
            id=strawberry.ID(str(message_id)),
            user_id=strawberry.ID(user_id),
            text=text,
        )

    async def history(self, limit: int) -> list[ChatMessage]:
        if self._db is None:
            raise RuntimeError("Baza danych nie jest otwarta")
        limit = max(1, min(limit, 50))
        async with self._lock:
            cursor = await self._db.execute(
                "SELECT id, user_id, text FROM chat_messages "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
            await cursor.close()
        return [
            ChatMessage(
                id=strawberry.ID(str(row[0])),
                user_id=strawberry.ID(row[1]),
                text=row[2],
            )
            for row in reversed(rows)
        ]


class MessageEvents:
    def __init__(self) -> None:
        self._queues: set[asyncio.Queue[ChatMessage]] = set()

    async def publish(self, message: ChatMessage) -> None:
        for queue in tuple(self._queues):
            queue.put_nowait(message)

    async def listen(self) -> AsyncGenerator[ChatMessage, None]:
        queue: asyncio.Queue[ChatMessage] = asyncio.Queue()
        self._queues.add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._queues.discard(queue)


@strawberry.type
class Query:
    @strawberry.field
    async def chat_history(
        self, info: strawberry.Info, limit: int = 50
    ) -> list[ChatMessage]:
        return await info.context["store"].history(limit)

    @strawberry.field
    def user_profile(
        self, info: strawberry.Info, id: strawberry.ID
    ) -> UserProfile | None:
        return info.context["profiles"].get(str(id))


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def send_message(
        self, info: strawberry.Info, user_id: strawberry.ID, text: str
    ) -> ChatMessage:
        user_key = str(user_id)
        if user_key not in info.context["profiles"]:
            raise ValueError("Nieznany użytkownik")
        if not text.strip() or len(text) > 1000:
            raise ValueError("Niepoprawna wiadomość")

        message = await info.context["store"].add(user_key, text.strip())
        await info.context["events"].publish(message)
        return message


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def message_added(
        self, info: strawberry.Info
    ) -> AsyncGenerator[ChatMessage, None]:
        async for message in info.context["events"].listen():
            yield message


schema = strawberry.Schema(
    query=Query, mutation=Mutation, subscription=Subscription
)


class ChatGraphQLView(GraphQLView):
    async def get_context(
        self, request: web.Request, response: web.StreamResponse
    ) -> dict[str, Any]:
        return {
            "store": request.app["store"],
            "events": request.app["events"],
            "profiles": request.app["profiles"],
        }


async def on_startup(app: web.Application) -> None:
    await app["store"].open()


async def on_cleanup(app: web.Application) -> None:
    await app["store"].close()


def create_app(database_path: str | Path) -> web.Application:
    app = web.Application()
    app["store"] = ChatStore(database_path)
    app["events"] = MessageEvents()
    app["profiles"] = {
        "1": UserProfile(id=strawberry.ID("1"), name="Jan", email="jan@example.com"),
        "2": UserProfile(id=strawberry.ID("2"), name="Anna", email="anna@example.com"),
    }
    app.router.add_route(
        "*",
        "/graphql",
        ChatGraphQLView(
            schema=schema,
            subscription_protocols=[GRAPHQL_TRANSPORT_WS_PROTOCOL],
        ),
    )
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__ == "__main__":
    web.run_app(create_app("graphql_chat.sqlite3"), host="127.0.0.1", port=8000)

