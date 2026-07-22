# app/models.py
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy import Float, ForeignKey, String, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, selectinload


class Base(DeclarativeBase):
    pass


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    books: Mapped[list[Book]] = relationship(back_populates="author")


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"), nullable=False)
    author: Mapped[Author] = relationship(back_populates="books")


# app/database.py
engine = create_async_engine("sqlite+aiosqlite:///./books.db")
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# app/schemas.py
class BookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    price: float
    author_id: int


class AuthorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr


# app/routers/authors.py
app = FastAPI()


@app.get("/authors/{author_id}/books", response_model=list[BookResponse])
async def get_author_books(author_id: int, session: AsyncSession = Depends(get_session)):
    author = await session.scalar(
        select(Author).options(selectinload(Author.books)).where(Author.id == author_id)
    )
    if author is None:
        raise HTTPException(status_code=404, detail="Author not found")
    return author.books
