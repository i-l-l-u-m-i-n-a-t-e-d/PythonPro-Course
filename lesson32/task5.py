from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
books: dict[int, dict[str, object]] = {}
next_book_id = 1


class BookCreate(BaseModel):
    title: str
    author: str


@app.get("/books")
async def list_books():
    return list(books.values())


@app.get("/books/{book_id}")
async def get_book(book_id: int):
    if book_id not in books:
        raise HTTPException(status_code=404, detail="Book not found")
    return books[book_id]


@app.post("/books")
async def create_book(book: BookCreate):
    global next_book_id
    created = {"id": next_book_id, **book.model_dump()}
    books[next_book_id] = created
    next_book_id += 1
    return created


@app.delete("/books/{book_id}")
async def delete_book(book_id: int):
    if book_id not in books:
        raise HTTPException(status_code=404, detail="Book not found")
    del books[book_id]
    return {"message": "Book deleted"}
