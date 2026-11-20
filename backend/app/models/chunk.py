from sqlalchemy import (
    Integer,
    Text,
    ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Chunk(Base):
    """
    Représente un passage de texte extrait d'une
    version de document lors de l'indexation RAG.
    """

    __tablename__ = "chunks"

    # Identifiant unique du passage
    id_chunk: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # Version du document dont provient le passage
    id_version: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "doc_versions.id_version",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    # Contenu textuel du passage
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    # Numéro de page d'origine, si disponible
    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    # Position du passage dans le document
    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
