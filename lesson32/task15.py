# app/services/book_tasks.py
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, status

EMAIL_LOG = Path("book_emails.log")
STATS_PATH = Path("book_stats.json")


def write_book_creation_email(book_id: int, title: str) -> None:
    with EMAIL_LOG.open("a", encoding="utf-8") as file:
        file.write(f"{datetime.now(timezone.utc).isoformat()} new book #{book_id}: {title}\n")


def update_book_statistics(book_id: int) -> None:
    try:
        data = json.loads(STATS_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data["deleted_books"] = int(data.get("deleted_books", 0)) + 1
    data["last_deleted_book_id"] = book_id
    temporary = STATS_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(data), encoding="utf-8")
    os.replace(temporary, STATS_PATH)


# app/routers/books.py
app = FastAPI()
books = {1: {"id": 1, "title": "Example"}}


@app.post("/books", status_code=status.HTTP_201_CREATED)
async def create_book(title: str, background_tasks: BackgroundTasks):
    book_id = max(books, default=0) + 1
    books[book_id] = {"id": book_id, "title": title}
    background_tasks.add_task(write_book_creation_email, book_id, title)
    return books[book_id]


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: int, background_tasks: BackgroundTasks) -> None:
    if book_id not in books:
        raise HTTPException(status_code=404, detail="Book not found")
    del books[book_id]
    background_tasks.add_task(update_book_statistics, book_id)
