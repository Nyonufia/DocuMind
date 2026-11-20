
from datetime import datetime, timezone

from sqlalchemy import (
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    LargeBinary,
    UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DocVersion(Base):
    """
    Représente une version d'un document.

    Chaque version conserve son propre fichier et son
    état d'indexation pour permettre le suivi du RAG.
    """

    __tablename__ = "doc_versions"

    # Empêcher deux versions portant le même numéro
    # pour un même document
    __table_args__ = (
        UniqueConstraint(
            "id_doc",
            "version_num",
            name="uq_document_version"
        ),
    )

    # Identifiant unique de la version
    id_version: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # Document auquel appartient cette version
    id_doc: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.id_doc", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Numéro de version : 1, 2, 3...
    version_num: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    # État du traitement documentaire
    statut: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        nullable=False
    )

    # Date de création de la version
    date_version: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Commentaire facultatif sur la version
    commentaire: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    # Contenu binaire du fichier importé
    contenu: Mapped[bytes] = mapped_column(
        LargeBinary().with_variant(
            LargeBinary(length=16777215),
            "mysql"
        ),
        nullable=False
    )

    # Empreinte SHA-256 du fichier
    digest: Mapped[str] = mapped_column(
        String(64),
        nullable=False
    )

    # Message d'erreur en cas d'échec d'indexation
    erreur_indexation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
