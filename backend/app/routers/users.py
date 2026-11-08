
# Gestion des comptes utilisateurs de DocuMind.
# Seuls les administrateurs autorisés peuvent créer des comptes.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.role import Role
from app.schemas.user import UserCreate
from app.security.dependencies import get_db, require_admin
from app.security.password import hash_password
from app.security.temporary_password import generate_temporary_password


router = APIRouter(
    prefix="/users",
    tags=["Gestion des utilisateurs"]
)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):

    # Vérifier que le nom d'utilisateur ou l'email
    # n'est pas déjà utilisé dans la base de données.
    existing_user = db.scalar(
        select(User).where(
            or_(
                User.username == data.username,
                User.email == str(data.email)
            )
        )
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Nom d'utilisateur ou email deja utilise"
        )

    # Vérifier que le rôle demandé existe.
    role = db.get(Role, data.id_role)

    if role is None:
        raise HTTPException(
            status_code=404,
            detail="Role introuvable"
        )

    # Générer un mot de passe temporaire sécurisé.
    # Seul son hachage sera enregistré dans MySQL.
    temporary_password = generate_temporary_password()

    new_user = User(
        nom=data.nom,
        prenom=data.prenom,
        username=data.username,
        email=str(data.email),
        password_hash=hash_password(temporary_password),
        id_role=role.id_role,
        est_actif=True,
        doit_changer_password=True
    )

    # Enregistrer le nouvel utilisateur.
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Retourner le mot de passe temporaire une seule fois.
    # Ne jamais l'enregistrer dans les journaux.
    return {
        "message": "Utilisateur cree avec succes",
        "id_user": new_user.id_user,
        "username": new_user.username,
        "email": new_user.email,
        "role": role.intitule,
        "temporary_password": temporary_password,
        "doit_changer_password": new_user.doit_changer_password
    }
