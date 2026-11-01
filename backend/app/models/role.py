
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Role(Base):
    __tablename__ = "roles"

    id_role: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    intitule: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    permissions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="role"
    )
