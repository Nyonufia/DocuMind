from datetime import datetime, timezone

from sqlalchemy import (
    Integer,
    String,
    Boolean,
    DateTime
)

from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# Modèle représentant une collection de documents.
# Une collection regroupe des documents soumis
# à des règles d'accès définies.
class Collection(Base):

    __tablename__ = "collections"

    # Identifiant unique de la collection.
    id_collection: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # Nom permettant d'identifier la collection.
    collection_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    # Description facultative de la collection.
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    # Date de création enregistrée automatiquement.
    date_creation: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Niveau d'accès associé à la collection.
    # Les valeurs autorisées seront définies
    # lors de l'implémentation des permissions.
    niveau_acces: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    # Indique si la collection est active.
    est_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
