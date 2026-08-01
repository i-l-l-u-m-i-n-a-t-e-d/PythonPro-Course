# .private/tasks_15_20/task17.py
from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

import strawberry
from aiohttp import web
from strawberry.aiohttp.views import GraphQLView
from strawberry.dataloader import DataLoader


@strawberry.type
class Post:
    id: strawberry.ID
    title: str
    author_id: strawberry.ID


@strawberry.type
class User:
    id: strawberry.ID
    name: str

    @strawberry.field
    async def posts(self, info: strawberry.Info) -> list[Post]:
        loader: DataLoader[strawberry.ID, list[Post]] = info.context["posts_loader"]
        return await loader.load(self.id)


class PostRepository:
    def __init__(self) -> None:
        self.users = [
            User(id=strawberry.ID("1"), name="Jan"),
            User(id=strawberry.ID("2"), name="Anna"),
            User(id=strawberry.ID("3"), name="Ola"),
        ]
        self.posts = [
            Post(id=strawberry.ID("1"), title="Python", author_id=strawberry.ID("1")),
            Post(id=strawberry.ID("2"), title="GraphQL", author_id=strawberry.ID("1")),
            Post(id=strawberry.ID("3"), title="Async", author_id=strawberry.ID("2")),
        ]
    async def posts_for_user_ids(
        self, user_ids: Sequence[strawberry.ID]
    ) -> list[list[Post]]:
        await asyncio.sleep(0)  # Give sibling GraphQL fields one batching turn.
        grouped: dict[strawberry.ID, list[Post]] = defaultdict(list)
        for post in self.posts:
            grouped[post.author_id].append(post)
        return [grouped[user_id] for user_id in user_ids]


@strawberry.type
class Query:
    @strawberry.field
    def users(self, info: strawberry.Info) -> list[User]:
        return list(info.context["repository"].users)


schema = strawberry.Schema(query=Query)


class DataLoaderGraphQLView(GraphQLView):
    async def get_context(
        self, request: web.Request, response: web.StreamResponse
    ) -> dict[str, Any]:
        repository: PostRepository = request.app["repository"]
        return {
            "repository": repository,
            "posts_loader": DataLoader(load_fn=repository.posts_for_user_ids),
        }


def create_app(repository: PostRepository | None = None) -> web.Application:
    app = web.Application()
    app["repository"] = repository or PostRepository()
    app.router.add_route("*", "/graphql", DataLoaderGraphQLView(schema=schema))
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="127.0.0.1", port=8000)

