
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.security.password import verify_password
from app.security.jwt_handler import create_access_token

#from app.security.dependencies import get_current_user
from app.security.dependencies import get_db, get_current_user

from app.schemas.auth import ChangePasswordRequest
from app.security.dependencies import get_current_user
from app.security.password import hash_password

from app.security.dependencies import require_password_changed

from app.security.dependencies import require_admin
from app.services.audit_service import create_audit_event, create_independent_audit_event

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.scalar(
        select(User).where(
            User.username == form_data.username
        )
    )

    """if user is None or not verify_password(
        form_data.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.est_actif:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce compte est desactive"
        )"""

    # Vérifier l'existence du compte et la validité du mot de passe.
    # Le message d'erreur reste identique pour éviter de révéler
    # si un nom d'utilisateur existe dans la base de données.
    if user is None or not verify_password(form_data.password, user.password_hash):
        # Journaliser la tentative échouée sans conserver le mot de passe.
        create_independent_audit_event(
            id_user=user.id_user if user else None,
            action="LOGIN_FAILURE",
            module="AUTH",
            statut="FAILURE",
            details="Tentative de connexion avec des identifiants incorrects"
        )

        raise HTTPException(
            status_code=401,
            detail="Identifiants incorrects"
        )

    # Refuser l'accès aux comptes désactivés.
    if not user.est_actif:
        # Conserver une trace de la connexion refusée.
        create_independent_audit_event(
            id_user=user.id_user,
            action="LOGIN_DENIED",
            module="AUTH",
            statut="DENIED",
            details="Tentative de connexion avec un compte desactive"
        )

        raise HTTPException(
            status_code=403,
            detail="Compte desactive"
        )

    # Générer un jeton JWT pour l'utilisateur authentifié.
    access_token = create_access_token(
        user_id=user.id_user,
        token_version=user.token_version
    )

    # Enregistrer la connexion réussie dans le journal d'audit.
    # Cette opération concerne tous les rôles de DocuMind.
    create_audit_event(
        db=db,
        id_user=user.id_user,
        action="LOGIN_SUCCESS",
        module="AUTH",
        statut="SUCCESS",
        details=f"Connexion reussie de l'utilisateur {user.username}"
    )

    # Valider l'enregistrement de l'événement.
    db.commit()

    # Retourner le jeton d'authentification au client.
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "doit_changer_password": user.doit_changer_password
    }


@router.get("/me")
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return {
        "id_user": current_user.id_user,
        "nom": current_user.nom,
        "prenom": current_user.prenom,
        "username": current_user.username,
        "email": current_user.email,
        "id_role": current_user.id_role,
        "est_actif": current_user.est_actif,
        "doit_changer_password": current_user.doit_changer_password
    }


# Modification du mot de passe de l'utilisateur connecté.
# Cette route sera également utilisée lors de la première connexion.

@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # Vérifier que l'ancien mot de passe est correct.
    if not verify_password(
        data.ancien_password,
        current_user.password_hash
    ):
        raise HTTPException(
            status_code=400,
            detail="Ancien mot de passe incorrect"
        )

    # Vérifier la confirmation et empêcher la réutilisation
    # du mot de passe actuel.
    if data.nouveau_password != data.confirmation_password:
        raise HTTPException(
            status_code=400,
            detail="Les nouveaux mots de passe ne correspondent pas"
        )

    if verify_password(
        data.nouveau_password,
        current_user.password_hash
    ):
        raise HTTPException(
            status_code=400,
            detail="Le nouveau mot de passe doit etre different"
        )

    # Enregistrer le nouveau mot de passe sous forme de hash.
    # Désactiver l'obligation de changement après validation.
    current_user.password_hash = hash_password(data.nouveau_password)
    current_user.doit_changer_password = False

    # Invalider les anciens jetons JWT de l'utilisateur.
    current_user.token_version += 1

    # Journaliser le changement de mot de passe.
    # Ne jamais enregistrer le mot de passe ni son hash dans l'audit.
    create_audit_event(
        db=db,
        id_user=current_user.id_user,
        action="PASSWORD_CHANGED",
        module="AUTH",
        statut="SUCCESS",
        details=(
            f"Changement de mot de passe du compte "
            f"{current_user.username}"
        )
    )

    # Valider le changement et l'événement d'audit ensemble.
    db.commit()

    return {
        "message": "Mot de passe modifie avec succes",
        "doit_changer_password": False
    }


# Route temporaire pour tester le blocage d'accès.
# Elle sera supprimée lorsque les vraies routes documentaires
# utiliseront require_password_changed.

@router.get("/test-access")
def test_access(
    current_user: User = Depends(require_password_changed)
):
    return {
        "message": "Acces autorise a DocuMind",
        "username": current_user.username
    }


# Route temporaire pour vérifier les droits administrateur.

@router.get("/test-admin")
def test_admin(
    current_user: User = Depends(require_admin)
):
    return {
        "message": "Acces administrateur autorise",
        "username": current_user.username
    }
