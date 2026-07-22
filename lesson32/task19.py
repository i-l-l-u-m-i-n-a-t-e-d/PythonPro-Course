# app/database.py
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import DateTime, ForeignKey, String, Text, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, selectinload

engine = create_async_engine("sqlite+aiosqlite:///./blog.db")
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


# app/models.py
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    posts: Mapped[list[Post]] = relationship(back_populates="author", cascade="all, delete-orphan")
    comments: Mapped[list[Comment]] = relationship(back_populates="author", cascade="all, delete-orphan")


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    author: Mapped[User] = relationship(back_populates="posts")
    comments: Mapped[list[Comment]] = relationship(back_populates="post", cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    post: Mapped[Post] = relationship(back_populates="comments")
    author: Mapped[User] = relationship(back_populates="comments")


# app/schemas.py
class ORMResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: EmailStr | None = None


class UserResponse(UserCreate, ORMResponse):
    id: int
    created_at: datetime


class PostCreate(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    content: str = Field(min_length=10)
    author_id: int


class PostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=5, max_length=200)
    content: str | None = Field(default=None, min_length=10)


class PostResponse(ORMResponse):
    id: int
    title: str
    content: str
    author_id: int
    created_at: datetime


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    author_id: int


class CommentResponse(ORMResponse):
    id: int
    content: str
    post_id: int
    author_id: int
    created_at: datetime


class PostWithComments(PostResponse):
    author: UserResponse
    comments: list[CommentResponse] = Field(default_factory=list)


# app/dependencies.py
async def current_user_id(x_user_id: Annotated[int | None, Header()] = None) -> int:
    if x_user_id is None:
        raise HTTPException(status_code=401, detail="X-User-ID header is required")
    return x_user_id


# app/services.py
EMAIL_LOG = Path("comment_emails.log")


def write_comment_email(comment_id: int, post_id: int) -> None:
    with EMAIL_LOG.open("a", encoding="utf-8") as file:
        file.write(f"New comment #{comment_id} on post #{post_id}\n")


# app/routers/users.py
users_router = APIRouter(prefix="/users", tags=["Users"])
Session = Annotated[AsyncSession, Depends(get_session)]


async def user_or_404(user_id: int, session: AsyncSession) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@users_router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, session: Session):
    db_user = User(username=user.username, email=str(user.email))
    session.add(db_user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Username or email already exists") from None
    await session.refresh(db_user)
    return db_user


@users_router.get("", response_model=list[UserResponse])
async def list_users(session: Session):
    return list((await session.scalars(select(User).order_by(User.id))).all())


@users_router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, session: Session):
    return await user_or_404(user_id, session)


@users_router.patch("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, update: UserUpdate, session: Session):
    user = await user_or_404(user_id, session)
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(user, field, str(value) if field == "email" else value)
    await session.commit()
    await session.refresh(user)
    return user


@users_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, session: Session) -> None:
    await session.delete(await user_or_404(user_id, session))
    await session.commit()


# app/routers/posts.py
posts_router = APIRouter(prefix="/posts", tags=["Posts"])


async def post_or_404(post_id: int, session: AsyncSession) -> Post:
    post = await session.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


def require_owner(post: Post, actor_id: int) -> None:
    if post.author_id != actor_id:
        raise HTTPException(status_code=403, detail="Only the author may modify this post")


@posts_router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(post: PostCreate, session: Session):
    if await session.get(User, post.author_id) is None:
        raise HTTPException(status_code=404, detail="Author not found")
    db_post = Post(**post.model_dump())
    session.add(db_post)
    await session.commit()
    await session.refresh(db_post)
    return db_post


@posts_router.get("", response_model=list[PostResponse])
async def list_posts(session: Session):
    return list((await session.scalars(select(Post).order_by(Post.id))).all())


@posts_router.get("/{post_id}/with-comments", response_model=PostWithComments)
async def get_post_with_comments(post_id: int, session: Session):
    post = await session.scalar(
        select(Post)
        .options(selectinload(Post.author), selectinload(Post.comments))
        .where(Post.id == post_id)
    )
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@posts_router.get("/{post_id}", response_model=PostResponse)
async def get_post(post_id: int, session: Session):
    return await post_or_404(post_id, session)


@posts_router.patch("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    update: PostUpdate,
    actor_id: Annotated[int, Depends(current_user_id)],
    session: Session,
):
    post = await post_or_404(post_id, session)
    require_owner(post, actor_id)
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(post, field, value)
    await session.commit()
    await session.refresh(post)
    return post


@posts_router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    actor_id: Annotated[int, Depends(current_user_id)],
    session: Session,
) -> None:
    post = await post_or_404(post_id, session)
    require_owner(post, actor_id)
    await session.delete(post)
    await session.commit()


# app/routers/comments.py
comments_router = APIRouter(prefix="/posts/{post_id}/comments", tags=["Comments"])


@comments_router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    post_id: int,
    comment: CommentCreate,
    background_tasks: BackgroundTasks,
    session: Session,
):
    if await session.get(Post, post_id) is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if await session.get(User, comment.author_id) is None:
        raise HTTPException(status_code=404, detail="Comment author not found")
    db_comment = Comment(post_id=post_id, **comment.model_dump())
    session.add(db_comment)
    await session.commit()
    await session.refresh(db_comment)
    background_tasks.add_task(write_comment_email, db_comment.id, post_id)
    return db_comment


# app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(title="Blog API", lifespan=lifespan)
app.include_router(users_router)
app.include_router(posts_router)
app.include_router(comments_router)
