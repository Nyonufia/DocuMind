# Service centralisé de journalisation des événements DocuMind.
# Il enregistre les actions de tous les modules dans audit_events.
# Le commit est effectué par la fonction appelante.

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.audit_event import AuditEvent


def create_audit_event(
    db: Session,
    id_user: int | None,
    action: str,
    module: str,
    statut: str,
    details: str | None = None
) -> AuditEvent:

    # Préparer un événement d'audit.
    event = AuditEvent(
        id_user=id_user,
        action=action,
        module=module,
        statut=statut,
        details=details
    )

    # Ajouter l'événement à la transaction en cours.
    db.add(event)

    return event

def create_independent_audit_event(
    id_user: int | None,
    action: str,
    module: str,
    statut: str,
    details: str | None = None
) -> None:

    # Créer une session dédiée uniquement au journal d'audit.
    with SessionLocal() as audit_db:
        try:
            create_audit_event(
                db=audit_db,
                id_user=id_user,
                action=action,
                module=module,
                statut=statut,
                details=details
            )

            # Valider l'événement indépendamment de la requête principale.
            audit_db.commit()

        except Exception:
            audit_db.rollback()
            raise
