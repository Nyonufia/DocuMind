from datetime import datetime, timezone

from sqlalchemy import (
    Integer,
    Text,
    Boolean,
    DateTime,
    ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Answer(Base):
    """
    Représente une réponse générée par l'assistant RAG.

    La réponse est associée à une question et indique
    si le système a dû s'abstenir de répondre.
    """

    __tablename__ = "answers"

    # Identifiant unique de la réponse
    id_answer: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # Question à laquelle correspond la réponse
    id_query: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "queries.id_query",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    # Texte de la réponse générée
    answer_text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    # Indique si l'assistant s'est abstenu de répondre
    abstained: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    # Date de génération de la réponse
    date_answer: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
