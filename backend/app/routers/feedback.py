# Routes de gestion des évaluations des réponses RAG.

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session

from app.models.answer import Answer
from app.models.query import Query
from app.models.feedback import Feedback
from app.models.user import User
from app.models.role import Role

from app.security.dependencies import (
    get_db,
    require_password_changed
)

router = APIRouter(
    prefix="/feedback",
    tags=["Feedback et qualité"]
)


# Schéma de validation d'une évaluation.
class FeedbackCreate(BaseModel):
    id_answer: int = Field(gt=0)
    est_utile: bool
    commentaire: str | None = Field(
        default=None,
        max_length=2000
    )


# Convertir une évaluation en réponse JSON.
def formater_feedback(feedback: Feedback):
    return {
        "id_feedback": feedback.id_feedback,
        "id_answer": feedback.id_answer,
        "id_user": feedback.id_user,
        "est_utile": feedback.est_utile,
        "commentaire": feedback.commentaire,
        "date_feedback": feedback.date_feedback
    }


# Vérifier que l'utilisateur est administrateur.
def verifier_administrateur(
    db: Session,
    current_user: User
):
    role = db.get(Role, current_user.id_role)

    if role is None or role.intitule != "Administrateur":
        raise HTTPException(
            status_code=403,
            detail="Accès réservé à l'administrateur."
        )


# Enregistrer ou modifier une évaluation.
@router.post("", status_code=201)
def soumettre_feedback(
    donnees: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_password_changed)
):
    # Vérifier que la réponse appartient à l'utilisateur.
    reponse = db.execute(
        select(Answer)
        .join(Query, Answer.id_query == Query.id_query)
        .where(
            Answer.id_answer == donnees.id_answer,
            Query.id_user == current_user.id_user
        )
    ).scalar_one_or_none()

    if reponse is None:
        raise HTTPException(
            status_code=404,
            detail="Réponse introuvable ou non autorisée."
        )

    # Rechercher une évaluation existante pour éviter
    # de créer plusieurs avis sur la même réponse.
    feedback = db.execute(
        select(Feedback).where(
            Feedback.id_answer == donnees.id_answer,
            Feedback.id_user == current_user.id_user
        )
    ).scalar_one_or_none()

    creation = feedback is None

    if creation:
        feedback = Feedback(
            id_answer=donnees.id_answer,
            id_user=current_user.id_user,
            est_utile=donnees.est_utile,
            commentaire=donnees.commentaire
        )
        db.add(feedback)
    else:
        feedback.est_utile = donnees.est_utile
        feedback.commentaire = donnees.commentaire

    try:
        db.commit()
        db.refresh(feedback)
    except Exception:
        db.rollback()
        raise

    return {
        "message": (
            "Évaluation enregistrée."
            if creation else "Évaluation mise à jour."
        ),
        "feedback": formater_feedback(feedback)
    }


# Consulter ses propres évaluations.
@router.get("/mes-evaluations")
def mes_evaluations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_password_changed)
):
    evaluations = db.scalars(
        select(Feedback)
        .where(Feedback.id_user == current_user.id_user)
        .order_by(
            Feedback.date_feedback.desc(),
            Feedback.id_feedback.desc()
        )
    ).all()

    return {
        "total": len(evaluations),
        "evaluations": [
            formater_feedback(f) for f in evaluations
        ]
    }



# Consulter les statistiques globales des évaluations.
@router.get("/statistiques")
def statistiques_feedback(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_password_changed)
):
    """
    Calcule les statistiques de satisfaction
    à partir des évaluations enregistrées.
    Accès réservé à l'administrateur.
    """

    # Vérifier les droits d'administration.
    verifier_administrateur(db, current_user)

    # Calculer le nombre total d'évaluations,
    # les réponses utiles et les réponses non utiles.
    # CASE WHEN est compatible avec MySQL.
    total, utiles, non_utiles = db.execute(
        select(
            func.count(Feedback.id_feedback),

            func.sum(
                case(
                    (Feedback.est_utile.is_(True), 1),
                    else_=0
                )
            ),

            func.sum(
                case(
                    (Feedback.est_utile.is_(False), 1),
                    else_=0
                )
            )
        )
    ).one()

    # Éviter les valeurs NULL lorsque la table est vide.
    total = total or 0
    utiles = utiles or 0
    non_utiles = non_utiles or 0

    # Calculer le pourcentage de satisfaction.
    taux = round(
        (utiles / total) * 100, 2
    ) if total > 0 else 0

    return {
        "total_evaluations": total,
        "reponses_utiles": utiles,
        "reponses_non_utiles": non_utiles,
        "taux_satisfaction": taux
    }


# Consulter toutes les évaluations des réponses RAG.
# Cette fonctionnalité est réservée à l'administrateur.
@router.get("")
def lister_feedbacks(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_password_changed)
):

    # Vérifier les autorisations administrateur.
    verifier_administrateur(db, current_user)

    # Récupérer les évaluations les plus récentes.
    evaluations = db.scalars(
        select(Feedback)
        .order_by(
            Feedback.date_feedback.desc(),
            Feedback.id_feedback.desc()
        )
    ).all()

    # Préparer les informations pour le frontend.
    feedbacks_list = []

    for feedback in evaluations:

        # Récupérer l'utilisateur ayant soumis l'avis.
        utilisateur = db.get(User, feedback.id_user)

        feedbacks_list.append({
            "id_feedback": feedback.id_feedback,
            "id_answer": feedback.id_answer,
            "id_user": feedback.id_user,
            "username": (
                utilisateur.username
                if utilisateur else "Utilisateur inconnu"
            ),
            "est_utile": feedback.est_utile,
            "commentaire": feedback.commentaire,
            "date_feedback": feedback.date_feedback
        })

    return {
        "total": len(feedbacks_list),
        "feedbacks": feedbacks_list
    }
