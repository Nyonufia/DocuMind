from datetime import datetime, timezone

from sqlalchemy import (
    Integer,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Text
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Embedding(Base):
    """
    Représente la vectorisation d'un passage documentaire.

    Le vecteur est conservé au format JSON dans MySQL.
    Il pourra être utilisé pour calculer la similarité
    entre une question et les passages indexés.
    """

    __tablename__ = "embeddings"

    # Empêcher plusieurs embeddings du même modèle
    # pour un même passage
    __table_args__ = (
        UniqueConstraint(
            "id_chunk",
            "model_name",
            name="uq_chunk_embedding_model"
        ),
    )

    # Identifiant unique de l'embedding
    id_embedding: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # Passage auquel appartient cet embedding
    id_chunk: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "chunks.id_chunk",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    # Nom du modèle utilisé pour la vectorisation
    model_name: Mapped[str] = mapped_column(
        String(160),
        nullable=False
    )

    # Représentation vectorielle sérialisée en JSON
    vector_reference: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    # Date de génération de l'embedding
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
