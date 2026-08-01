# .private/tasks_15_20/task15.py
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import strawberry
from aiohttp import web
from strawberry.aiohttp.views import GraphQLView
from strawberry.subscriptions import GRAPHQL_TRANSPORT_WS_PROTOCOL


@strawberry.type
class User:
    id: strawberry.ID
    name: str
    email: str


class UserEvents:
    """A small in-process event broker with cleanup for every subscriber."""

    def __init__(self) -> None:
        self._queues: set[asyncio.Queue[User]] = set()

    async def publish(self, user: User) -> None:
        for queue in tuple(self._queues):
            queue.put_nowait(user)

    async def listen(self) -> AsyncGenerator[User, None]:
        queue: asyncio.Queue[User] = asyncio.Queue()
        self._queues.add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._queues.discard(queue)


@strawberry.type
class Query:
    @strawberry.field
    def users(self, info: strawberry.Info) -> list[User]:
        return list(info.context["users"])


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_user(
        self, info: strawberry.Info, name: str, email: str
    ) -> User:
        if not name.strip() or "@" not in email:
            raise ValueError("Podaj poprawne imię i email")

        users: list[User] = info.context["users"]
        user = User(id=strawberry.ID(str(len(users) + 1)), name=name, email=email)
        users.append(user)
        await info.context["events"].publish(user)
        return user


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def user_registered(
        self, info: strawberry.Info
    ) -> AsyncGenerator[User, None]:
        async for user in info.context["events"].listen():
            yield user


schema = strawberry.Schema(
    query=Query, mutation=Mutation, subscription=Subscription
)


class UserGraphQLView(GraphQLView):
    async def get_context(
        self, request: web.Request, response: web.StreamResponse
    ) -> dict[str, Any]:
        return {
            "users": request.app["users"],
            "events": request.app["events"],
        }


def create_app() -> web.Application:
    app = web.Application()
    app["users"] = []
    app["events"] = UserEvents()
    app.router.add_route(
        "*",
        "/graphql",
        UserGraphQLView(
            schema=schema,
            subscription_protocols=[GRAPHQL_TRANSPORT_WS_PROTOCOL],
        ),
    )
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="127.0.0.1", port=8000)

