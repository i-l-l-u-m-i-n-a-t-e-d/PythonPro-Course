# app/routers/books.py
from fastapi import APIRouter, HTTPException

books_router = APIRouter(prefix="/books", tags=["Books"])
books: dict[int, dict[str, object]] = {}


@books_router.get("")
async def list_books():
    return list(books.values())


@books_router.get("/{book_id}")
async def get_book(book_id: int):
    if book_id not in books:
        raise HTTPException(status_code=404, detail="Book not found")
    return books[book_id]


# app/routers/authors.py
authors_router = APIRouter(prefix="/authors", tags=["Authors"])
authors: dict[int, dict[str, object]] = {}


@authors_router.get("")
async def list_authors():
    return list(authors.values())


@authors_router.get("/{author_id}")
async def get_author(author_id: int):
    if author_id not in authors:
        raise HTTPException(status_code=404, detail="Author not found")
    return authors[author_id]


# app/main.py
from fastapi import FastAPI

app = FastAPI()
app.include_router(books_router)
app.include_router(authors_router)
