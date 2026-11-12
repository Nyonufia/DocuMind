
# Routes de consultation du journal d'audit de DocuMind.
# Seuls les administrateurs peuvent consulter les événements.
# Aucune route de modification ou de suppression n'est exposée.

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent
from app.models.user import User
from app.security.dependencies import get_db, require_admin


router = APIRouter(
    prefix="/audit-events",
    tags=["Journal d'audit"]
)


@router.get("/")
def list_audit_events(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):

    # Compter le nombre total d'événements enregistrés.
    total = db.scalar(
        select(func.count(AuditEvent.id_event))
    )

    # Récupérer les événements du plus récent au plus ancien.
    events = db.scalars(
        select(AuditEvent)
        .order_by(
            AuditEvent.date_event.desc(),
            AuditEvent.id_event.desc()
        )
        .limit(100)
    ).all()

    # Préparer les informations à retourner à l'interface.
    result = []

    for event in events:
        result.append({
            "id_event": event.id_event,
            "id_user": event.id_user,
            "action": event.action,
            "module": event.module,
            "details": event.details,
            "statut": event.statut,
            "date_event": event.date_event
        })

    return {
        "total": total,
        "events": result
    }
