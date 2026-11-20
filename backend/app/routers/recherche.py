
# Route API de recherche documentaire sémantique.
# L'utilisateur doit être authentifié et avoir
# terminé le changement obligatoire de mot de passe.

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.security.dependencies import require_password_changed
from app.services.recherche_service import rechercher_passages
from app.services.generation_service import generer_reponse
from app.services.historique_service import (
    enregistrer_question,
    enregistrer_reponse,
    enregistrer_passages,
    consulter_historique,
    consulter_detail_historique
)


router = APIRouter(
    prefix="/recherche",
    tags=["Recherche documentaire"]
)


# Schéma de validation de la question.
class RechercheRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1500)


@router.post("/")
def effectuer_recherche(
    donnees: RechercheRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_password_changed)
):
    """
    Recherche les passages pertinents dans les
    documents autorisés de l'utilisateur connecté.
    """

    # Effectuer la recherche sémantique sécurisée.
    try:
        passages = rechercher_passages(
            db=db,
            id_user=current_user.id_user,
            question=donnees.question
        )

    except ValueError as erreur:
        raise HTTPException(
            status_code=400,
            detail=str(erreur)
        ) from erreur

    # Retourner les résultats classés par pertinence.
    return {
        "question": donnees.question,
        "nombre_resultats": len(passages),
        "passages": passages
    }


# Route RAG avec enregistrement de l'historique.
@router.post("/question")
def poser_question(
    donnees: RechercheRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_password_changed)
):
    """
    Recherche les passages autorisés, génère une réponse
    et enregistre l'historique dans une transaction MySQL.
    """

    # Rechercher les passages autorisés.
    try:
        passages = rechercher_passages(
            db=db,
            id_user=current_user.id_user,
            question=donnees.question
        )
    except ValueError as erreur:
        raise HTTPException(
            status_code=400,
            detail=str(erreur)
        ) from erreur

    # Préparer la réponse, avec abstention par défaut.
    message_abstention = (
        "Les documents accessibles ne contiennent "
        "pas suffisamment d'informations pour répondre."
    )

    reponse = message_abstention
    abstention = True

    # Générer une réponse uniquement si des passages
    # pertinents ont été retrouvés.
    if passages:
        texte_genere = generer_reponse(
            question=donnees.question,
            passages=passages
        )

        if texte_genere != "INFORMATION_INSUFFISANTE":
            reponse = texte_genere
            abstention = False

    # Enregistrer la question, les passages et la réponse
    # dans une seule transaction.
    try:
        question_enregistree = enregistrer_question(
            db=db,
            id_user=current_user.id_user,
            question=donnees.question
        )

        enregistrer_passages(
            db=db,
            id_query=question_enregistree.id_query,
            passages=passages
        )

        reponse_enregistree = enregistrer_reponse(
            db=db,
            id_query=question_enregistree.id_query,
            texte_reponse=reponse,
            abstention=abstention
        )

        # Valider les trois enregistrements ensemble.
        db.commit()

    except Exception:
        # Annuler les modifications non validées
        # si l'enregistrement échoue.
        db.rollback()
        raise

    # Ne retourner les sources que si une réponse
    # documentaire a effectivement été générée.
    return {
        "id_query": question_enregistree.id_query,
        "id_answer": reponse_enregistree.id_answer,
        "question": donnees.question,
        "reponse": reponse,
        "abstention": abstention,
        "sources": passages if not abstention else []
    }

# Route permettant de consulter l'historique
# des questions et réponses de l'utilisateur connecté.
@router.get("/historique")
def obtenir_historique(
    limite: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_password_changed)
):
    """
    Retourne les dernières questions et réponses
    appartenant uniquement à l'utilisateur connecté.
    """

    # Récupérer l'historique personnel de l'utilisateur.
    try:
        historique = consulter_historique(
            db=db,
            id_user=current_user.id_user,
            limite=limite
        )

    except ValueError as erreur:
        raise HTTPException(
            status_code=400,
            detail=str(erreur)
        ) from erreur

    # Retourner les résultats de l'historique.
    return {
        "nombre_resultats": len(historique),
        "historique": historique
    }


# Route de consultation détaillée de l'historique.
# Les autorisations documentaires sont vérifiées
# avant de retourner une ancienne réponse.
@router.get("/historique/{id_query}")
def obtenir_detail_historique(
    id_query: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_password_changed)
):
    """
    Retourne une ancienne question, sa réponse
    et les passages documentaires encore autorisés.
    """

    # Rechercher la question appartenant
    # à l'utilisateur actuellement connecté.
    resultat = consulter_detail_historique(
        db=db,
        id_user=current_user.id_user,
        id_query=id_query
    )

    # Ne pas révéler l'existence d'une question
    # appartenant à un autre utilisateur.
    if resultat is None:
        raise HTTPException(
            status_code=404,
            detail="Question introuvable."
        )

    # Refuser l'accès si les autorisations
    # documentaires ont changé.
    if resultat.get("acces_revoque"):
        raise HTTPException(
            status_code=403,
            detail=resultat["message"]
        )

    return resultat
