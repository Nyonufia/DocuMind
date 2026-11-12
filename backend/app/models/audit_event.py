
# Modèle SQLAlchemy du journal d'audit centralisé.
# Il permet d'enregistrer les actions importantes effectuées
# dans les différents modules de DocuMind.

from datetime import datetime, timezone

from sqlalchemy import (
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    # Identifiant unique de l'événement.
    id_event: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # Utilisateur ayant effectué l'action.
    # Peut être NULL pour une tentative de connexion inconnue.
    id_user: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id_user", ondelete="SET NULL"),
        nullable=True
    )

    # Informations décrivant l'événement.
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    module: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    statut: Mapped[str] = mapped_column(String(20), nullable=False)

    # Date et heure de l'événement en UTC.
    date_event: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relation avec le compte utilisateur.
    user = relationship("User")
