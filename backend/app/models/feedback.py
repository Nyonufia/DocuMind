from datetime import datetime, timezone

from sqlalchemy import (
    Integer,
    Boolean,
    Text,
    DateTime,
    ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column


from app.database import Base


class Feedback(Base):
    """
    Représente l'évaluation d'une réponse par un utilisateur.

    Permet de recueillir les avis sur la pertinence
    et la qualité des réponses de l'assistant RAG.
    """

    __tablename__ = "feedbacks"

    # Identifiant unique de l'évaluation
    id_feedback: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # Réponse évaluée
    id_answer: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "answers.id_answer",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    # Utilisateur ayant donné son avis
    id_user: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id_user"),
        nullable=False,
        index=True
    )

    # True = réponse utile, False = réponse non utile
    est_utile: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False
    )

    # Commentaire facultatif de l'utilisateur
    commentaire: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    # Date de soumission de l'évaluation
    date_feedback: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
