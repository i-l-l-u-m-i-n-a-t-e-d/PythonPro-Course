# app/models.py
from sqlalchemy import Integer, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    balance: Mapped[int] = mapped_column(Integer)


# app/handlers.py
from typing import Any

from aiohttp import web
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def positive_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise web.HTTPBadRequest(text=f"Pole {field_name} musi być dodatnią liczbą całkowitą")
    return value


async def transfer(request: web.Request) -> web.Response:
    try:
        data: dict[str, Any] = await request.json()
        from_id = positive_int(data["from_id"], "from_id")
        to_id = positive_int(data["to_id"], "to_id")
        amount = positive_int(data["amount"], "amount")
    except (KeyError, ValueError, TypeError) as error:
        raise web.HTTPBadRequest(text="Wymagane są poprawne from_id, to_id i amount") from error
    if from_id == to_id:
        raise web.HTTPBadRequest(text="Nie można wykonać przelewu na to samo konto")

    session_factory: async_sessionmaker[AsyncSession] = request.app["db_session_factory"]
    async with session_factory() as session:
        async with session.begin():
            accounts = (
                await session.scalars(
                    select(Account)
                    .where(Account.id.in_([from_id, to_id]))
                    .with_for_update()
                )
            ).all()
            accounts_by_id = {account.id: account for account in accounts}
            source = accounts_by_id.get(from_id)
            destination = accounts_by_id.get(to_id)
            if source is None or destination is None:
                raise web.HTTPNotFound(text="Nie znaleziono jednego z kont")
            if source.balance < amount:
                raise web.HTTPBadRequest(text="Niewystarczające środki")
            source.balance -= amount
            destination.balance += amount
            result = {
                "from_id": from_id,
                "to_id": to_id,
                "amount": amount,
                "from_balance": source.balance,
                "to_balance": destination.balance,
            }
    return web.json_response(result)


# app/routes.py
def setup_routes(app: web.Application) -> None:
    app.router.add_post("/transfer", transfer)
