# Gestion des collections documentaires de DocuMind.
# La création est réservée aux administrateurs et aux éditeurs.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.models.collection import Collection
from app.models.user import User
from app.schemas.collection import CollectionCreate, CollectionUpdate, CollectionResponse

from app.security.dependencies import get_db, require_admin_or_editor, require_password_changed
from app.services.audit_service import create_audit_event

from app.models.user_collection import user_collections

from app.models.role import Role


# Vérifier exclusivement le rôle Éditeur pour les attributions.
# La vérification est réalisée côté backend à partir du rôle en base.
def require_editor_for_assignments(
    current_user: User = Depends(require_password_changed),
    db: Session = Depends(get_db)
) -> User:
    role = db.get(Role, current_user.id_role)
    if role is None or role.intitule != "Éditeur":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul un editeur peut attribuer ou retirer un utilisateur d'une collection"
        )
    if not current_user.est_actif:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte utilisateur desactive"
        )
    return current_user


# Définition des routes de gestion des collections.
router = APIRouter(
    prefix="/collections",
    tags=["Gestion des collections"]
)


# Création d'une nouvelle collection documentaire.
# L'utilisateur doit être authentifié et posséder
# le rôle Administrateur ou Éditeur.

@router.post(
    "/",
    response_model=CollectionResponse,
    status_code=status.HTTP_201_CREATED
)
def create_collection(
    data: CollectionCreate,
    current_user: User = Depends(require_admin_or_editor),
    db: Session = Depends(get_db)
):
    # Vérifier qu'une collection portant le même nom
    # n'existe pas déjà, sans tenir compte de la casse.
    collection_name = data.collection_name.strip()

    if not collection_name:
        raise HTTPException(
            status_code=422,
            detail="Le nom de la collection ne peut pas etre vide"
        )

    existing_collection = db.scalar(
        select(Collection).where(
            Collection.collection_name == collection_name
        )
    )

    if existing_collection is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Une collection portant ce nom existe deja"
        )

    # Préparer la nouvelle collection.
    # La date de création et le statut actif
    # sont renseignés par le modèle SQLAlchemy.
    new_collection = Collection(
        collection_name=collection_name,
        description=data.description,
        niveau_acces=data.niveau_acces.strip(),
        est_active=True
    )

    # Ajouter la collection à la transaction.
    db.add(new_collection)

    try:
        # Envoyer l'insertion à MySQL pour obtenir
        # l'identifiant sans valider la transaction.
        db.flush()

        # Enregistrer la création dans le journal d'audit.
        create_audit_event(
            db=db,
            id_user=current_user.id_user,
            action="COLLECTION_CREATED",
            module="COLLECTIONS",
            statut="SUCCESS",
            details=(
                f"Creation de la collection "
                f"{new_collection.collection_name} "
                f"(ID : {new_collection.id_collection})"
            )
        )

        # Valider la collection et l'audit ensemble.
        db.commit()

    except Exception:
        # Annuler les modifications si une erreur survient.
        db.rollback()
        raise

    # Actualiser l'objet après son enregistrement.
    db.refresh(new_collection)

    return new_collection



# Consultation des collections selon le rôle.
# Les administrateurs et éditeurs voient toutes les collections.
# Les employés voient uniquement leurs collections actives.

@router.get("/", response_model=list[CollectionResponse])
def list_collections(
    current_user: User = Depends(require_password_changed),
    db: Session = Depends(get_db)
):
    # Identifier le rôle de l'utilisateur connecté.
    role = db.get(Role, current_user.id_role)

    if role is None:
        raise HTTPException(
            status_code=403,
            detail="Role utilisateur introuvable"
        )

    # Administrateur et éditeur :
    # accès à la liste complète des collections.
    if role.intitule in ("Administrateur", "Éditeur"):
        statement = select(Collection).order_by(
            Collection.id_collection
        )

    # Employé :
    # accès uniquement aux collections actives
    # auxquelles il est personnellement associé.
    elif role.intitule == "Employé":
        statement = (
            select(Collection)
            .join(
                user_collections,
                Collection.id_collection
                == user_collections.c.id_collection
            )
            .where(
                user_collections.c.id_user == current_user.id_user,
                Collection.est_active.is_(True)
            )
            .order_by(Collection.id_collection)
        )

    # Tout autre rôle est refusé.
    else:
        raise HTTPException(
            status_code=403,
            detail="Acces non autorise"
        )

    # Exécuter la requête adaptée au rôle.
    return db.scalars(statement).all()


# Consultation des utilisateurs disponibles pour les collections.
# Seul l'Éditeur peut accéder à cette liste.
# Aucune information administrative sensible n'est retournée.

@router.get("/utilisateurs-disponibles")
def list_available_users(
    current_user: User = Depends(require_editor_for_assignments),
    db: Session = Depends(get_db)
):
    # Récupérer uniquement les utilisateurs actifs.
    utilisateurs = db.scalars(
        select(User)
        .where(User.est_actif.is_(True))
        .order_by(User.username)
    ).all()

    # Retourner uniquement les données nécessaires
    # pour attribuer un accès documentaire.
    return {
        "total": len(utilisateurs),
        "users": [
            {
                "id_user": utilisateur.id_user,
                "username": utilisateur.username,
                "nom": utilisateur.nom,
                "prenom": utilisateur.prenom
            }
            for utilisateur in utilisateurs
        ]
    }


# Consultation des informations d'une collection précise.
# Seuls les administrateurs et les éditeurs peuvent
# accéder à cette route pour le moment.

@router.get(
    "/{id_collection}",
    response_model=CollectionResponse
)
def get_collection(
    id_collection: int,
    current_user: User = Depends(require_admin_or_editor),
    db: Session = Depends(get_db)
):
    # Rechercher la collection dans MySQL
    # à partir de son identifiant.
    collection = db.get(Collection, id_collection)

    # Retourner une erreur si la collection
    # demandée n'existe pas.
    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection introuvable"
        )

    # Retourner les informations de la collection.
    # Le schéma CollectionResponse définit les champs
    # qui seront envoyés au frontend React.
    return collection


# Modification des informations d'une collection.
# Cette opération est réservée aux administrateurs
# et aux éditeurs autorisés.

@router.patch(
    "/{id_collection}",
    response_model=CollectionResponse
)
def update_collection(
    id_collection: int,
    data: CollectionUpdate,
    current_user: User = Depends(require_admin_or_editor),
    db: Session = Depends(get_db)
):
    # Rechercher la collection concernée.
    collection = db.get(Collection, id_collection)

    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection introuvable"
        )

    # Récupérer uniquement les champs transmis.
    updates = data.model_dump(exclude_unset=True)

    # Le statut est_active sera géré par une route dédiée.
    if "est_active" in updates:
        raise HTTPException(
            status_code=422,
            detail="Utilisez la route dediee pour changer le statut"
        )

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="Aucune modification fournie"
        )

    # Les champs obligatoires ne peuvent pas être nuls.
    for field in ("collection_name", "niveau_acces"):
        if field in updates and updates[field] is None:
            raise HTTPException(
                status_code=422,
                detail=f"Le champ {field} ne peut pas etre nul"
            )

    # Nettoyer et valider le nom de la collection.
    if "collection_name" in updates:
        name = updates["collection_name"].strip()

        if len(name) < 2:
            raise HTTPException(
                status_code=422,
                detail="Le nom doit contenir au moins 2 caracteres"
            )

        # Vérifier qu'une autre collection
        # ne porte pas déjà ce nom.
        existing = db.scalar(
            select(Collection).where(
                Collection.collection_name == name,
                Collection.id_collection != id_collection
            )
        )

        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="Une collection portant ce nom existe deja"
            )

        updates["collection_name"] = name

    # Appliquer uniquement les champs autorisés.
    for field, value in updates.items():
        setattr(collection, field, value)

    try:
        # Enregistrer l'événement dans le journal d'audit.
        # Ne conserver que les noms des champs modifiés.
        create_audit_event(
            db=db,
            id_user=current_user.id_user,
            action="COLLECTION_UPDATED",
            module="COLLECTIONS",
            statut="SUCCESS",
            details=(
                f"Modification de la collection "
                f"ID {collection.id_collection}. "
                f"Champs : {', '.join(updates.keys())}"
            )
        )

        # Valider la modification et l'audit ensemble.
        db.commit()

    except Exception:
        # Annuler la transaction en cas d'erreur.
        db.rollback()
        raise

    # Actualiser les informations depuis MySQL.
    db.refresh(collection)

    return collection


# Activation ou désactivation d'une collection.
# Cette opération est réservée aux administrateurs
# et aux éditeurs autorisés.

@router.patch(
    "/{id_collection}/status",
    response_model=CollectionResponse
)
def update_collection_status(
    id_collection: int,
    est_active: bool,
    current_user: User = Depends(require_admin_or_editor),
    db: Session = Depends(get_db)
):
    # Rechercher la collection concernée.
    collection = db.get(Collection, id_collection)

    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection introuvable"
        )

    # Ne rien modifier si la collection possède
    # déjà le statut demandé.
    if collection.est_active == est_active:
        return collection

    # Modifier le statut de la collection.
    collection.est_active = est_active

    # Déterminer l'action à enregistrer dans l'audit.
    if est_active:
        audit_action = "COLLECTION_ACTIVATED"
        description = "Activation"
    else:
        audit_action = "COLLECTION_DEACTIVATED"
        description = "Desactivation"

    try:
        # Enregistrer l'événement dans le journal d'audit.
        create_audit_event(
            db=db,
            id_user=current_user.id_user,
            action=audit_action,
            module="COLLECTIONS",
            statut="SUCCESS",
            details=(
                f"{description} de la collection "
                f"{collection.collection_name} "
                f"(ID : {collection.id_collection})"
            )
        )

        # Valider le changement de statut et son audit
        # dans une seule transaction.
        db.commit()

    except Exception:
        # Annuler les modifications en cas d'erreur.
        db.rollback()
        raise

    # Actualiser les informations depuis MySQL.
    db.refresh(collection)

    return collection


# Association d'un utilisateur à une collection.
# Seul l'Éditeur peut attribuer des collections aux utilisateurs.

@router.post(
    "/{id_collection}/users/{id_user}",
    status_code=status.HTTP_201_CREATED
)
def add_user_to_collection(
    id_collection: int,
    id_user: int,
    current_user: User = Depends(require_editor_for_assignments),
    db: Session = Depends(get_db)
):
    # Vérifier que la collection existe.
    collection = db.get(Collection, id_collection)

    if collection is None:
        raise HTTPException(
            status_code=404,
            detail="Collection introuvable"
        )

    # Empêcher l'attribution d'une collection désactivée.
    if not collection.est_active:
        raise HTTPException(
            status_code=409,
            detail="Impossible d'attribuer une collection desactivee"
        )

    # Vérifier que l'utilisateur existe.
    user = db.get(User, id_user)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Utilisateur introuvable"
        )

    # Empêcher l'attribution à un compte désactivé.
    if not user.est_actif:
        raise HTTPException(
            status_code=403,
            detail="Impossible d'attribuer une collection a un compte desactive"
        )

    # Vérifier si l'association existe déjà.
    existing = db.execute(
        select(user_collections).where(
            user_collections.c.id_user == id_user,
            user_collections.c.id_collection == id_collection
        )
    ).first()

    if existing is not None:
        return {
            "message": "Utilisateur deja associe a cette collection",
            "id_user": id_user,
            "id_collection": id_collection
        }

    try:
        # Créer l'association dans la table intermédiaire.
        db.execute(
            insert(user_collections).values(
                id_user=id_user,
                id_collection=id_collection
            )
        )

        # Journaliser l'attribution de la collection.
        create_audit_event(
            db=db,
            id_user=current_user.id_user,
            action="COLLECTION_USER_ADDED",
            module="COLLECTIONS",
            statut="SUCCESS",
            details=(
                f"Attribution de la collection "
                f"{collection.collection_name} "
                f"(ID : {id_collection}) "
                f"a l'utilisateur {user.username} "
                f"(ID : {id_user})"
            )
        )

        # Valider l'association et l'audit ensemble.
        db.commit()

    except Exception:
        # Annuler la transaction en cas d'erreur.
        db.rollback()
        raise

    return {
        "message": "Utilisateur associe a la collection avec succes",
        "id_user": id_user,
        "id_collection": id_collection
    }



# Consultation des utilisateurs associés à une collection.
# Accessible uniquement aux administrateurs et aux éditeurs.

@router.get("/{id_collection}/users")
def get_collection_users(
    id_collection: int,
    current_user: User = Depends(require_admin_or_editor),
    db: Session = Depends(get_db)
):
    # Vérifier que la collection existe.
    collection = db.get(Collection, id_collection)

    if collection is None:
        raise HTTPException(
            status_code=404,
            detail="Collection introuvable"
        )

    # Récupérer les utilisateurs associés à la collection.
    # La jointure utilise la table intermédiaire user_collections.
    statement = (
        select(User)
        .join(
            user_collections,
            User.id_user == user_collections.c.id_user
        )
        .where(
            user_collections.c.id_collection == id_collection
        )
        .order_by(User.id_user)
    )

    users = db.scalars(statement).all()

    # Retourner uniquement les informations nécessaires.
    # Ne jamais exposer les mots de passe ou leurs empreintes.
    return {
        "id_collection": collection.id_collection,
        "collection_name": collection.collection_name,
        "nombre_utilisateurs": len(users),
        "utilisateurs": [
            {
                "id_user": user.id_user,
                "username": user.username,
                "est_actif": user.est_actif
            }
            for user in users
        ]
    }


# Consultation des collections attribuées à un utilisateur.
# Accessible aux administrateurs et aux éditeurs.

@router.get("/users/{id_user}")
def get_user_collections(
    id_user: int,
    current_user: User = Depends(require_admin_or_editor),
    db: Session = Depends(get_db)
):
    # Vérifier que l'utilisateur existe.
    user = db.get(User, id_user)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Utilisateur introuvable"
        )

    # Rechercher les collections associées à l'utilisateur
    # à travers la table intermédiaire user_collections.
    statement = (
        select(Collection)
        .join(
            user_collections,
            Collection.id_collection
            == user_collections.c.id_collection
        )
        .where(
            user_collections.c.id_user == id_user
        )
        .order_by(Collection.id_collection)
    )

    collections = db.scalars(statement).all()

    # Retourner les collections et leurs informations.
    return {
        "id_user": user.id_user,
        "username": user.username,
        "nombre_collections": len(collections),
        "collections": [
            {
                "id_collection": collection.id_collection,
                "collection_name": collection.collection_name,
                "niveau_acces": collection.niveau_acces,
                "est_active": collection.est_active
            }
            for collection in collections
        ]
    }

# Retrait d'un utilisateur d'une collection.
# Seul l'Éditeur peut retirer une attribution.
# Le retrait de la dernière collection reste autorisé.

@router.delete("/{id_collection}/users/{id_user}")
def remove_user_from_collection(
    id_collection: int,
    id_user: int,
    current_user: User = Depends(require_editor_for_assignments),
    db: Session = Depends(get_db)
):
    # Vérifier l'existence de la collection.
    collection = db.get(Collection, id_collection)

    if collection is None:
        raise HTTPException(
            status_code=404,
            detail="Collection introuvable"
        )

    # Vérifier l'existence de l'utilisateur.
    user = db.get(User, id_user)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Utilisateur introuvable"
        )

    # Vérifier que l'association existe.
    association = db.execute(
        select(user_collections).where(
            user_collections.c.id_user == id_user,
            user_collections.c.id_collection == id_collection
        )
    ).first()

    if association is None:
        raise HTTPException(
            status_code=404,
            detail="Utilisateur non associe a cette collection"
        )

    try:
        # Supprimer uniquement l'association.
        db.execute(
            delete(user_collections).where(
                user_collections.c.id_user == id_user,
                user_collections.c.id_collection == id_collection
            )
        )

        # Enregistrer l'opération dans le journal d'audit.
        create_audit_event(
            db=db,
            id_user=current_user.id_user,
            action="COLLECTION_USER_REMOVED",
            module="COLLECTIONS",
            statut="SUCCESS",
            details=(
                f"Retrait de l'utilisateur {user.username} "
                f"(ID : {id_user}) de la collection "
                f"{collection.collection_name} "
                f"(ID : {id_collection})"
            )
        )

        # Valider le retrait et l'audit ensemble.
        db.commit()

    except Exception:
        # Annuler les modifications en cas d'erreur.
        db.rollback()
        raise

    return {
        "message": "Utilisateur retire de la collection avec succes",
        "id_user": id_user,
        "id_collection": id_collection
    }
