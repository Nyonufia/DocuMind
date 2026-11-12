# Gestion des comptes utilisateurs de DocuMind.
# Seuls les administrateurs autorisés peuvent créer des comptes.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.role import Role
from app.schemas.user import UserCreate, UserUpdate, UserRoleUpdate, UserStatusUpdate

from app.security.dependencies import get_db, require_admin
from app.security.password import hash_password
from app.security.temporary_password import generate_temporary_password

from app.services.audit_service import create_audit_event


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
    #db.add(new_user)
    #db.commit()
    #db.refresh(new_user)

    # Enregistrer le nouvel utilisateur dans la session.
    db.add(new_user)

    # Envoyer l'insertion à MySQL pour obtenir son identifiant.
    # La transaction n'est pas encore validée.
    #db.flush() permet d'envoyer les modifications à MySQL sans terminer la transaction.
    db.flush()

    # Enregistrer l'événement dans le journal d'audit centralisé.
    create_audit_event(
        db=db,
        id_user=admin.id_user,
        action="USER_CREATED",
        module="USERS",
        statut="SUCCESS",
        details=f"Creation du compte utilisateur : {new_user.username}"
    )

    # Valider la création du compte et son événement d'audit ensemble.
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


# Consultation de la liste des utilisateurs.
# Seul un administrateur peut accéder aux informations des comptes.
# Les mots de passe hachés ne sont jamais retournés.

@router.get("/")
def list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):

    # Récupérer les utilisateurs et leurs rôles depuis MySQL.
    results = db.execute(
        select(User, Role.intitule)
        .join(Role, User.id_role == Role.id_role)
        .order_by(User.id_user)
    ).all()

    # Préparer les informations à retourner au frontend.
    users_list = []

    for user, role_name in results:
        users_list.append({
            "id_user": user.id_user,
            "nom": user.nom,
            "prenom": user.prenom,
            "username": user.username,
            "email": user.email,
            "id_role": user.id_role,
            "role": role_name,
            "est_actif": user.est_actif,
            "doit_changer_password": user.doit_changer_password,
            "date_creation": user.date_creation
        })

    return {
        "total": len(users_list),
        "users": users_list
    }


# Consultation des informations d'un utilisateur précis.
# Cette opération est réservée aux administrateurs.
# Le mot de passe haché n'est jamais retourné.

@router.get("/{id_user}")
def get_user(
    id_user: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):

    # Rechercher l'utilisateur à partir de son identifiant.
    user = db.get(User, id_user)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable"
        )

    # Récupérer le rôle associé à l'utilisateur.
    role = db.get(Role, user.id_role)

    # Retourner uniquement les informations autorisées.
    return {
        "id_user": user.id_user,
        "nom": user.nom,
        "prenom": user.prenom,
        "username": user.username,
        "email": user.email,
        "id_role": user.id_role,
        "role": role.intitule if role else None,
        "est_actif": user.est_actif,
        "doit_changer_password": user.doit_changer_password,
        "date_creation": user.date_creation,
        "last_connexion": user.last_connexion
    }


# Modification des informations d'un utilisateur existant.
# Seul un administrateur peut effectuer cette opération.
# Le rôle, le statut et le mot de passe ne sont pas modifiés ici.

@router.patch("/{id_user}")
def update_user(
    id_user: int,
    data: UserUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):

    # Rechercher le compte à modifier.
    user = db.get(User, id_user)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Utilisateur introuvable"
        )

    # Récupérer uniquement les champs envoyés.
    updates = data.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="Aucune modification fournie"
        )

    # Refuser les valeurs nulles pour les champs obligatoires.
    if any(value is None for value in updates.values()):
        raise HTTPException(
            status_code=422,
            detail="Les champs ne peuvent pas etre nuls"
        )

    # Vérifier les doublons de nom d'utilisateur et d'email.
    if "username" in updates:
        existing = db.scalar(
            select(User).where(
                User.username == updates["username"],
                User.id_user != id_user
            )
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail="Nom d'utilisateur deja utilise"
            )

    if "email" in updates:
        existing = db.scalar(
            select(User).where(
                User.email == str(updates["email"]),
                User.id_user != id_user
            )
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail="Adresse email deja utilisee"
            )

    # Appliquer uniquement les modifications autorisées.
    """for field, value in updates.items():
        setattr(user, field, str(value) if field == "email" else value)

    db.commit()
    db.refresh(user)"""

    # Appliquer uniquement les modifications autorisées.
    for field, value in updates.items():
        setattr(user, field, str(value) if field == "email" else value)

    # Enregistrer l'événement de modification.
    # Nous conservons les noms des champs modifiés,
    # sans enregistrer leurs anciennes ou nouvelles valeurs.
    create_audit_event(
        db=db,
        id_user=admin.id_user,
        action="USER_UPDATED",
        module="USERS",
        statut="SUCCESS",
        details=(
            f"Modification du compte ID {user.id_user} "
            f"({user.username}). "
            f"Champs : {', '.join(updates.keys())}"
        )
    )

    # Valider la modification et son événement d'audit ensemble.
    db.commit()
    db.refresh(user)

    return {
        "message": "Utilisateur modifie avec succes",
        "user": {
            "id_user": user.id_user,
            "nom": user.nom,
            "prenom": user.prenom,
            "username": user.username,
            "email": user.email,
            "id_role": user.id_role,
            "est_actif": user.est_actif,
            "doit_changer_password": user.doit_changer_password
        }
    }



# Modification du rôle d'un utilisateur par un administrateur.
# Le système protège le dernier administrateur actif
# et conserve une trace des changements dans le journal d'audit.

@router.patch("/{id_user}/role")
def update_user_role(
    id_user: int,
    data: UserRoleUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):

    # Rechercher l'utilisateur concerné.
    user = db.get(User, id_user)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Utilisateur introuvable"
        )

    # Vérifier que le nouveau rôle existe.
    new_role = db.get(Role, data.id_role)

    if new_role is None:
        raise HTTPException(
            status_code=404,
            detail="Role introuvable"
        )

    # Récupérer le rôle actuel de l'utilisateur.
    current_role = db.get(Role, user.id_role)

    # Empêcher le retrait du dernier administrateur actif.
    if (
        current_role is not None
        and current_role.intitule == "Administrateur"
        and new_role.intitule != "Administrateur"
        and user.est_actif
    ):
        active_admins = db.scalars(
            select(User)
            .join(Role, User.id_role == Role.id_role)
            .where(
                Role.intitule == "Administrateur",
                User.est_actif.is_(True)
            )
        ).all()

        if len(active_admins) <= 1:
            raise HTTPException(
                status_code=409,
                detail="Impossible de retirer le dernier administrateur actif"
            )

    # Ne rien modifier si le rôle demandé est déjà attribué.
    if user.id_role == new_role.id_role:
        return {
            "message": "Cet utilisateur possède déjà ce rôle",
            "id_user": user.id_user,
            "nouveau_role": new_role.intitule
        }

    # Conserver l'ancien rôle avant la modification.
    ancien_role = current_role.intitule if current_role else "Inconnu"

    # Appliquer le nouveau rôle.
    user.id_role = new_role.id_role

    # Invalider les anciens JWT pour forcer la reconnexion.
    user.token_version += 1

    # Journaliser le changement de rôle.
    create_audit_event(
        db=db,
        id_user=admin.id_user,
        action="USER_ROLE_CHANGED",
        module="USERS",
        statut="SUCCESS",
        details=(
            f"Modification du rôle de {user.username} "
            f"(ID : {user.id_user}) : "
            f"{ancien_role} vers {new_role.intitule}"
        )
    )

    # Valider la modification et l'événement d'audit ensemble.
    db.commit()

    return {
        "message": "Role modifie avec succes",
        "id_user": user.id_user,
        "nouveau_role": new_role.intitule
    }



# Activation ou désactivation d'un compte utilisateur.
# Seul un administrateur peut modifier le statut d'un compte.
# La désactivation de son propre compte est interdite.

@router.patch("/{id_user}/status")
def update_user_status(
    id_user: int,
    data: UserStatusUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):

    # Rechercher l'utilisateur concerné.
    user = db.get(User, id_user)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Utilisateur introuvable"
        )

    # Empêcher un administrateur de désactiver son propre compte.
    if user.id_user == admin.id_user and not data.est_actif:
        raise HTTPException(
            status_code=403,
            detail="Vous ne pouvez pas desactiver votre propre compte"
        )

    # Vérifier le rôle du compte à désactiver.
    role = db.get(Role, user.id_role)

    if (
        not data.est_actif
        and user.est_actif
        and role is not None
        and role.intitule == "Administrateur"
    ):
        # Vérifier qu'un autre administrateur actif existe.
        other_admin = db.scalar(
            select(User)
            .join(Role, User.id_role == Role.id_role)
            .where(
                Role.intitule == "Administrateur",
                User.est_actif.is_(True),
                User.id_user != user.id_user
            )
        )

        if other_admin is None:
            raise HTTPException(
                status_code=409,
                detail="Impossible de desactiver le dernier administrateur actif"
            )

    # Ne rien modifier si le compte possède déjà ce statut.
    if user.est_actif == data.est_actif:
        return {
            "message": "Le compte possede deja ce statut",
            "id_user": user.id_user,
            "est_actif": user.est_actif
        }

    # Modifier le statut et invalider les anciennes sessions.
    """user.est_actif = data.est_actif
    user.token_version += 1

    db.commit()"""

    # Vérifier si le statut demandé est déjà celui du compte.
    # Cela évite une modification et un événement d'audit inutiles.
    if user.est_actif == data.est_actif:
        return {
            "message": "Le compte possède déjà ce statut",
            "id_user": user.id_user,
            "est_actif": user.est_actif
        }

    # Modifier le statut du compte.
    user.est_actif = data.est_actif

    # Invalider les anciens jetons JWT.
    user.token_version += 1

    # Déterminer l'action à enregistrer selon le nouveau statut.
    if user.est_actif:
        audit_action = "USER_ACTIVATED"
        description = "Activation"
    else:
        audit_action = "USER_DEACTIVATED"
        description = "Desactivation"

    # Enregistrer l'événement dans le journal centralisé.
    create_audit_event(
        db=db,
        id_user=admin.id_user,
        action=audit_action,
        module="USERS",
        statut="SUCCESS",
        details=(
            f"{description} du compte {user.username} "
            f"(ID : {user.id_user})"
        )
    )

    # Valider le changement de statut et son audit ensemble.
    db.commit()
    db.refresh(user)

    return {
        "message": (
            "Compte active avec succes"
            if user.est_actif
            else "Compte desactive avec succes"
        ),
        "id_user": user.id_user,
        "username": user.username,
        "est_actif": user.est_actif
    }


# Réinitialisation du mot de passe d'un utilisateur.
# Cette opération est réservée aux administrateurs.
# Le mot de passe temporaire est retourné une seule fois.

@router.post("/{id_user}/reset-password")
def reset_user_password(
    id_user: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):

    # Rechercher le compte utilisateur concerné.
    user = db.get(User, id_user)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Utilisateur introuvable"
        )

    # Empêcher un administrateur de réinitialiser son propre compte.
    # Un autre administrateur pourra le faire si nécessaire.

    if user.id_user == admin.id_user:
        raise HTTPException(
            status_code=403,
            detail="Vous ne pouvez pas reinitialiser votre propre mot de passe"
        )

    # Empêcher la réinitialisation d'un compte désactivé.
    if not user.est_actif:
        raise HTTPException(
            status_code=403,
            detail="Impossible de reinitialiser un compte desactive"
        )

    # Générer et hacher le nouveau mot de passe temporaire.
    temporary_password = generate_temporary_password()

    """user.password_hash = hash_password(temporary_password)

    # Forcer le changement à la prochaine connexion.
    user.doit_changer_password = True

    # Invalider toutes les anciennes sessions JWT.
    user.token_version += 1

    # Enregistrer les modifications dans MySQL.
    db.commit()"""

    # Enregistrer le nouveau mot de passe temporaire sous forme de hash.
    # L'utilisateur devra le modifier à sa prochaine connexion.
    user.password_hash = hash_password(temporary_password)
    user.doit_changer_password = True

    # Invalider les anciennes sessions de l'utilisateur.
    user.token_version += 1

    # Conserver une trace de la réinitialisation.
    # Aucun mot de passe ni hash n'est enregistré dans l'audit.
    create_audit_event(
        db=db,
        id_user=admin.id_user,
        action="PASSWORD_RESET",
        module="USERS",
        statut="SUCCESS",
        details=(
            f"Reinitialisation du mot de passe du compte "
            f"{user.username} (ID : {user.id_user})"
        )
    )

    # Enregistrer la réinitialisation et l'audit dans une seule transaction.
    db.commit()

    return {
        "message": "Mot de passe reinitialise avec succes",
        "id_user": user.id_user,
        "username": user.username,
        "temporary_password": temporary_password,
        "doit_changer_password": True
    }
