
from datetime import datetime, timezone

from sqlalchemy import (
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id_user: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    nom: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    prenom: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    date_creation: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    last_connexion: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    est_actif: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    id_role: Mapped[int] = mapped_column(
        ForeignKey("roles.id_role"),
        nullable=False
    )

    role: Mapped["Role"] = relationship(
        "Role",
        back_populates="users"
    )
