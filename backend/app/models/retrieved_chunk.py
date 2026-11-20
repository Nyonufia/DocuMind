from sqlalchemy import (
    Integer,
    Float,
    ForeignKey,
    UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RetrievedChunk(Base):
    """
    Représente un passage documentaire retrouvé
    lors de la recherche RAG pour une question.
    """

    __tablename__ = "retrieved_chunks"

    # Éviter de retrouver deux fois le même passage
    # pour une question donnée
    __table_args__ = (
        UniqueConstraint(
            "id_query",
            "id_chunk",
            name="uq_query_chunk"
        ),
    )

    # Identifiant unique du résultat
    id_retrieved_chunk: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # Question à laquelle le passage est associé
    id_query: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "queries.id_query",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    # Passage documentaire retrouvé
    id_chunk: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chunks.id_chunk"),
        nullable=False,
        index=True
    )

    # Score de pertinence calculé par le moteur RAG
    score: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    # Position du passage dans les résultats
    rang: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
