
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

    if user is None or not verify_password(
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
        )

    # Générer un JWT associé à la version actuelle du compte.
    token = create_access_token(
        user.id_user,
        user.token_version
    )

    return {
        "access_token": token,
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

    # Enregistrer le nouveau mot de passe sous forme hachée.
    current_user.password_hash = hash_password(
        data.nouveau_password
    )

    # Supprimer l'obligation de changement du mot de passe.
    current_user.doit_changer_password = False

    # Augmenter la version pour invalider tous les anciens JWT.
    current_user.token_version += 1

    # Enregistrer les modifications dans MySQL.
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
