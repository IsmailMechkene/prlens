from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# User.role. There is no self-serve path to ADMIN — a compromised admin session
# could otherwise mint more admins — so it is only ever granted out of band, by
# scripts/set_admin.py.
ROLE_USER = "user"
ROLE_ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    github_id: Mapped[int] = mapped_column(unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    # Indexed but NOT unique: a handle is a GitHub login, which can be renamed and
    # then re-registered by somebody else. github_id above is the identity. A unique
    # handle turned that rename into an IntegrityError on an otherwise valid login.
    handle: Mapped[str] = mapped_column(String(100), index=True)
    initials: Mapped[str] = mapped_column(String(10))
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ROLE_USER or ROLE_ADMIN. An admin keeps an ordinary account — their own
    # installations, their own dashboard — and additionally sees the /api/admin
    # views across every user. server_default, not just a Python-side default, so
    # the rows an older deployment already has are backfilled by the ALTER in
    # database.connection rather than left NULL.
    role: Mapped[str] = mapped_column(
        String(20),
        default=ROLE_USER,
        server_default=ROLE_USER,
        nullable=False,
    )

    installations: Mapped[list["Installation"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    github_token: Mapped[str | None] = mapped_column(Text, nullable=True)


class Installation(Base):
    __tablename__ = "installations"
    __table_args__ = (UniqueConstraint("user_id", "repo_name", name="uq_user_repo"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )

    repo_name: Mapped[str] = mapped_column(String(150))
    owner: Mapped[str] = mapped_column(String(100))
    visibility: Mapped[str] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    active: Mapped[bool] = mapped_column(Boolean, default=True)
    connected: Mapped[bool] = mapped_column(Boolean, default=False)

    min_severity: Mapped[str] = mapped_column(String(20))
    languages: Mapped[list] = mapped_column(JSON)
    approve_threshold: Mapped[int] = mapped_column(Integer)
    changes_threshold: Mapped[int] = mapped_column(Integer)
    excluded_files: Mapped[list] = mapped_column(JSON)
    reviewer_map: Mapped[dict] = mapped_column(JSON)

    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    user: Mapped["User"] = relationship(back_populates="installations")

    reviews: Mapped[list["Review"]] = relationship(
        back_populates="installation",
        cascade="all, delete-orphan",
    )


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)

    installation_id: Mapped[int] = mapped_column(
        ForeignKey("installations.id", ondelete="CASCADE")
    )

    pr_number: Mapped[int] = mapped_column(Integer)
    pr_title: Mapped[str] = mapped_column(String(255))

    score: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30))

    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    installation: Mapped["Installation"] = relationship(
        back_populates="reviews"
    )

    comments: Mapped[list["ReviewComment"]] = relationship(
        back_populates="review",
        cascade="all, delete-orphan",
    )


class ReviewComment(Base):
    __tablename__ = "review_comments"

    id: Mapped[int] = mapped_column(primary_key=True)

    review_id: Mapped[int] = mapped_column(
        ForeignKey("reviews.id", ondelete="CASCADE")
    )

    file_path: Mapped[str] = mapped_column(Text)
    line: Mapped[int] = mapped_column(Integer)

    type: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))

    message: Mapped[str] = mapped_column(Text)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)

    review: Mapped["Review"] = relationship(back_populates="comments")