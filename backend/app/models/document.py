
from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime, ForeignKey, BigInteger, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from sqlalchemy import Boolean

class Document(Base):
    """
    Représente un document appartenant à une collection.
    Le contenu du fichier sera stocké dans ses versions.
    """

    __tablename__ = "documents"

    # Identifiant unique du document
    id_doc: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # Informations générales du document
    titre: Mapped[str] = mapped_column(
        String(180),
        nullable=False
    )

    date_ajout: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    type_fichier: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    taille: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
    )

    # Collection contenant le document
    id_collection: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("collections.id_collection"),
        nullable=False,
        index=True
    )

    # Utilisateur ayant ajouté le document
    id_user: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id_user"),
        nullable=False
    )
    # Gestion de la suppression logique du document.
    # False : document actif.
    # True : document supprimé logiquement.
    est_supprime: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0"
    )
