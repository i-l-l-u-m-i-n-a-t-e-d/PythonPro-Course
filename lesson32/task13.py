# app/database.py
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Float, String, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

DATABASE_URL = "sqlite+aiosqlite:///./books.db"
engine = create_async_engine(DATABASE_URL)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def create_tables() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


# app/models.py
class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)


# app/schemas.py
class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    price: float = Field(gt=0)


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    price: float | None = Field(default=None, gt=0)


class BookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    price: float


# app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(lifespan=lifespan)


async def book_or_404(book_id: int, session: AsyncSession) -> Book:
    book = await session.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(book: BookCreate, session: AsyncSession = Depends(get_session)):
    db_book = Book(**book.model_dump())
    session.add(db_book)
    await session.commit()
    await session.refresh(db_book)
    return db_book


@app.get("/books", response_model=list[BookResponse])
async def list_books(session: AsyncSession = Depends(get_session)):
    return list((await session.scalars(select(Book).order_by(Book.id))).all())


@app.get("/books/{book_id}", response_model=BookResponse)
async def get_book(book_id: int, session: AsyncSession = Depends(get_session)):
    return await book_or_404(book_id, session)


@app.patch("/books/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: int,
    update: BookUpdate,
    session: AsyncSession = Depends(get_session),
):
    book = await book_or_404(book_id, session)
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(book, field, value)
    await session.commit()
    await session.refresh(book)
    return book


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: int, session: AsyncSession = Depends(get_session)) -> None:
    await session.delete(await book_or_404(book_id, session))
    await session.commit()
