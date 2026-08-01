# .private/tasks_8_14/task12.py
from __future__ import annotations

from aiohttp import web
import strawberry
from strawberry.aiohttp.views import GraphQLView


@strawberry.type
class User:
    id: strawberry.ID
    name: str
    email: str

    @strawberry.field
    def posts(self) -> list[Post]:
        return [post for post in fake_posts if post.author_id == self.id]


@strawberry.type
class Post:
    id: strawberry.ID
    title: str
    content: str
    author_id: strawberry.Private[strawberry.ID]

    @strawberry.field
    def author(self) -> User | None:
        return next(
            (user for user in fake_users if user.id == self.author_id), None
        )


fake_users = [
    User(id="1", name="Jan Kowalski", email="jan@example.com"),
    User(id="2", name="Anna Nowak", email="anna@example.com"),
    User(id="3", name="Piotr Zieliński", email="piotr@example.com"),
]
fake_posts = [
    Post(id="1", title="Python jest super", content="...", author_id="1"),
    Post(id="2", title="GraphQL tutorial", content="...", author_id="1"),
    Post(id="3", title="Asynchroniczność", content="...", author_id="2"),
]


@strawberry.type
class Query:
    @strawberry.field
    def user(self, id: strawberry.ID) -> User | None:
        return next((user for user in fake_users if user.id == id), None)

    @strawberry.field
    def users(self) -> list[User]:
        return fake_users

    @strawberry.field
    def posts(self, author_id: strawberry.ID | None = None) -> list[Post]:
        if author_id is None:
            return fake_posts
        return [post for post in fake_posts if post.author_id == author_id]

    @strawberry.field
    def search_users(self, name: str | None = None) -> list[User]:
        if not name:
            return fake_users
        searched_name = name.casefold()
        return [
            user for user in fake_users if searched_name in user.name.casefold()
        ]


schema = strawberry.Schema(query=Query)


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_route(
        "*", "/graphql", GraphQLView(schema=schema, graphql_ide="graphiql")
    )
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="localhost", port=8000)
