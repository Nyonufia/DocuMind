from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User
from app.security.jwt_handler import verify_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session invalide ou expiree",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = verify_access_token(token)

    if payload is None:
        raise credentials_exception

    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise credentials_exception

    user = db.get(User, user_id)

    if user is None:
        raise credentials_exception

    if not user.est_actif:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte desactive"
        )

    # Refuser les anciens JWT après un changement de mot de passe.
    # La version contenue dans le JWT doit correspondre à celle de MySQL.

    token_version = payload.get("ver")

    if (
            type(token_version) is not int
            or token_version != user.token_version
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalidee. Veuillez vous reconnecter.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


# Contrôle d'accès aux fonctionnalités de DocuMind.
# Un utilisateur doit avoir changé son mot de passe temporaire
# avant de pouvoir accéder aux routes protégées ordinaires.

def require_password_changed(
    current_user: User = Depends(get_current_user)
):
    if current_user.doit_changer_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous devez changer votre mot de passe avant de continuer"
        )

    return current_user



# Vérification des privilèges administrateur.
# Seul un administrateur ayant terminé le changement
# de son mot de passe temporaire peut gérer les utilisateurs.

def require_admin(
    current_user: User = Depends(require_password_changed),
    db: Session = Depends(get_db)
):
    # Vérifier que le rôle de l'utilisateur est Administrateur.
    from app.models.role import Role

    role = db.get(Role, current_user.id_role)

    if role is None or role.intitule != "Administrateur":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acces reserve aux administrateurs"
        )

    return current_user


# Vérification des privilèges de gestion documentaire.
# Seuls les administrateurs et les éditeurs peuvent
# effectuer les opérations de gestion des collections.
# Le changement du mot de passe temporaire reste obligatoire.

def require_admin_or_editor(
    current_user: User = Depends(require_password_changed),
    db: Session = Depends(get_db)
):
    # Importer le modèle Role pour identifier
    # le rôle attribué à l'utilisateur connecté.
    from app.models.role import Role

    # Récupérer le rôle depuis la base de données.
    role = db.get(Role, current_user.id_role)

    # Refuser l'accès si le rôle est inexistant
    # ou différent des deux rôles autorisés.
    if role is None or role.intitule not in ("Administrateur", "Éditeur"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acces reserve aux administrateurs et aux editeurs"
        )

    # Retourner l'utilisateur autorisé.
    return current_user
