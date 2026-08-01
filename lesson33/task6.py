# .private/tasks_1_7/task6.py
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


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_user(self, name: str, email: str) -> User:
        new_id = max((int(user.id) for user in fake_users), default=0) + 1
        user = User(id=strawberry.ID(str(new_id)), name=name, email=email)
        fake_users.append(user)
        return user


schema = strawberry.Schema(query=Query, mutation=Mutation)


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_route(
        "*", "/graphql", GraphQLView(schema=schema, graphql_ide="graphiql")
    )
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="localhost", port=8000)
