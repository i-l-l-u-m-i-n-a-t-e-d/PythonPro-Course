# .private/tasks_1_7/task5.py
from typing import Optional

import strawberry
from aiohttp import web
from strawberry.aiohttp.views import GraphQLView


@strawberry.type
class User:
    id: strawberry.ID
    name: str
    email: str


fake_users = [
    User(id=strawberry.ID("1"), name="Jan Kowalski", email="jan@example.com"),
    User(id=strawberry.ID("2"), name="Anna Nowak", email="anna@example.com"),
]


@strawberry.type
class Query:
    @strawberry.field
    def user(self, id: strawberry.ID) -> Optional[User]:
        return next((user for user in fake_users if user.id == id), None)

    @strawberry.field
    def users(self) -> list[User]:
        return fake_users


schema = strawberry.Schema(query=Query)


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_route(
        "*", "/graphql", GraphQLView(schema=schema, graphql_ide="graphiql")
    )
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="localhost", port=8000)
