from datetime import datetime, timezone

from sqlalchemy import Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Query(Base):
    """
    Représente une question posée par un utilisateur
    à l'assistant documentaire DocuMind.
    """

    __tablename__ = "queries"

    # Identifiant unique de la question
    id_query: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # Utilisateur ayant posé la question
    id_user: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id_user"),
        nullable=False,
        index=True
    )

    # Texte de la question
    question_text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    # Date et heure de la question
    date_query: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
