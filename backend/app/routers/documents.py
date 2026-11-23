from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, DocVersion, Collection
from app.models.user import User
from app.models.role import Role
from app.models.user_collection import user_collections

from app.security.dependencies import (
    get_db,
    require_admin_or_editor,
    require_password_changed
)
from app.services.document_service import preparer_document
from app.services.indexation_service import indexer_document

from io import BytesIO
from urllib.parse import quote

from fastapi.responses import StreamingResponse
from app.services.audit_service import create_independent_audit_event

from sqlalchemy import func
from app.models.audit_event import AuditEvent

router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)


# Centraliser les autorisations documentaires par rôle.
# Éditeur : toutes les collections actives sans association.
# Administrateur et Employé : uniquement les collections attribuées.
# La vérification du statut actif reste effectuée dans chaque route.
def acces_collection_autorise(db: Session, current_user: User, id_collection: int) -> bool:
    role = db.get(Role, current_user.id_role)

    if role is None:
        return False

    if role.intitule == "Éditeur":
        return True

    if role.intitule not in ("Administrateur", "Employé"):
        return False

    association = db.execute(
        select(user_collections.c.id_user).where(
            user_collections.c.id_user == current_user.id_user,
            user_collections.c.id_collection == id_collection
        )
    ).first()

    return association is not None


@router.post("/upload", status_code=201)
async def importer_document(
    id_collection: int = Form(...),
    fichier: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_editor)
):
    """
    Importe un document dans une collection autorisée.

    Enregistre les métadonnées dans Document et
    le fichier original dans DocVersion.
    """

    # Vérifier que la collection existe et est active.
    collection = db.get(Collection, id_collection)

    if collection is None or not collection.est_active:
        raise HTTPException(
            status_code=404,
            detail="Collection introuvable ou inactive"
        )

    # Vérifier l'appartenance de l'utilisateur
    # à la collection documentaire.
    # Les éditeurs ont un accès global ; les administrateurs doivent être associés.
    if not acces_collection_autorise(db, current_user, id_collection):
        raise HTTPException(
            status_code=403,
            detail="Vous n'avez pas accès à cette collection"
        )

    # Vérifier le fichier et préparer ses métadonnées.
    donnees = await preparer_document(fichier)

    try:
        # Enregistrer les informations générales.
        document = Document(
            titre=donnees["nom_fichier"],
            type_fichier=donnees["type_fichier"],
            taille=donnees["taille"],
            id_collection=id_collection,
            id_user=current_user.id_user
        )

        db.add(document)
        db.flush()

        # Créer la première version du document.
        version = DocVersion(
            id_doc=document.id_doc,
            version_num=1,
            statut="pending",
            contenu=donnees["contenu"],
            digest=donnees["digest"]
        )

        db.add(version)
        db.flush()

        # Valider les deux enregistrements ensemble.
        resultat = {
            "message": "Document importé avec succès",
            "id_document": document.id_doc,
            "id_version": version.id_version,
            "nom_fichier": document.titre,
            "id_collection": id_collection,
            "statut": version.statut
        }

        db.commit()
        return resultat

    except Exception:
        # Annuler les insertions en cas d'erreur.
        db.rollback()
        raise

    finally:
        await fichier.close()



@router.post("/{id_document}/indexer")
def lancer_indexation(
    id_document: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_editor)
):
    """
    Lance l'indexation complète d'un document :
    extraction, découpage, génération des embeddings
    et enregistrement dans MySQL.

    Les éditeurs peuvent indexer dans toutes les collections actives.
    Les administrateurs doivent être associés à la collection.
    """

    # Rechercher le document demandé.
    document = db.get(Document, id_document)

    # Refuser l'indexation des documents supprimés.
    if document is None or document.est_supprime:
        raise HTTPException(
            status_code=404,
            detail="Document introuvable"
        )

    # Vérifier que la collection est active.
    collection = db.get(Collection, document.id_collection)

    if collection is None or not collection.est_active:
        raise HTTPException(
            status_code=404,
            detail="Collection introuvable ou inactive"
        )

    # Vérifier les droits de l'utilisateur connecté.
    if not acces_collection_autorise(db, current_user, document.id_collection):
        raise HTTPException(
            status_code=403,
            detail="Accès refusé à cette collection"
        )

    # Récupérer la dernière version du document.
    version = db.execute(
        select(DocVersion)
        .where(DocVersion.id_doc == document.id_doc)
        .order_by(DocVersion.version_num.desc())
        .limit(1)
    ).scalar_one_or_none()

    if version is None:
        raise HTTPException(
            status_code=404,
            detail="Aucune version disponible pour ce document"
        )

    # Empêcher une nouvelle indexation si elle est terminée.
    if version.statut == "indexed":
        raise HTTPException(
            status_code=409,
            detail="Cette version est déjà indexée"
        )

    # Extraire le texte, créer les chunks et générer
    # les embeddings avec le modèle Ollama.
    try:
        nombre_chunks = indexer_document(
            db=db,
            document=document,
            version=version
        )

    except ValueError as erreur:
        raise HTTPException(
            status_code=400,
            detail=str(erreur)
        ) from erreur

    # Retourner le résultat de l'indexation complète.
    return {
        "message": "Indexation complète avec succès",
        "id_document": document.id_doc,
        "id_version": version.id_version,
        "nombre_chunks": nombre_chunks,
        "nombre_embeddings": nombre_chunks,
        "statut": version.statut
    }


# Suppression logique d'un document.
# Le document et ses données RAG restent conservés
# dans MySQL afin de préserver l'historique.
@router.delete("/{id_document}")
def supprimer_document(
    id_document: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_editor)
):
    """
    Supprime logiquement un document si l'utilisateur
    possède le rôle et les autorisations nécessaires.
    """

    # Rechercher le document demandé.
    document = db.get(Document, id_document)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document introuvable."
        )

    # Vérifier si le document est déjà supprimé.
    if document.est_supprime:
        raise HTTPException(
            status_code=404,
            detail="Document introuvable."
        )

    # Vérifier que sa collection existe et est active.
    collection = db.get(Collection, document.id_collection)

    if collection is None or not collection.est_active:
        raise HTTPException(
            status_code=404,
            detail="Collection introuvable ou inactive."
        )

    # Vérifier que l'utilisateur possède toujours
    # l'autorisation d'accéder à cette collection.
    if not acces_collection_autorise(db, current_user, document.id_collection):
        raise HTTPException(
            status_code=403,
            detail="Vous n'avez pas accès à cette collection."
        )

    # Effectuer la suppression logique.
    try:
        document.est_supprime = True

        db.commit()

        return {
            "message": "Document supprimé logiquement avec succès.",
            "id_document": document.id_doc,
            "titre": document.titre,
            "est_supprime": document.est_supprime
        }

    except Exception:
        # Annuler les modifications si une erreur survient.
        db.rollback()
        raise


# Restaurer un document supprimé logiquement.
# Cette opération est réservée aux administrateurs
# et éditeurs autorisés à accéder à la collection.
@router.patch("/{id_document}/restaurer")
def restaurer_document(
    id_document: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_editor)
):
    """
    Restaure un document supprimé logiquement
    sans modifier ses versions, chunks ou embeddings.
    """

    # Rechercher le document dans la base de données.
    document = db.get(Document, id_document)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document introuvable."
        )

    # Vérifier que la collection existe et est active.
    collection = db.get(Collection, document.id_collection)

    if collection is None or not collection.est_active:
        raise HTTPException(
            status_code=404,
            detail="Collection introuvable ou inactive."
        )

    # Vérifier l'autorisation d'accès à la collection.
    if not acces_collection_autorise(db, current_user, document.id_collection):
        raise HTTPException(
            status_code=403,
            detail="Vous n'avez pas accès à cette collection."
        )

    # Éviter de restaurer un document déjà actif.
    if not document.est_supprime:
        raise HTTPException(
            status_code=409,
            detail="Ce document est déjà actif."
        )

    # Restaurer le document dans une transaction.
    try:
        document.est_supprime = False
        db.commit()

        return {
            "message": "Document restauré avec succès.",
            "id_document": document.id_doc,
            "titre": document.titre,
            "est_supprime": document.est_supprime
        }

    except Exception:
        # Annuler les modifications en cas d'erreur.
        db.rollback()
        raise


# Afficher uniquement les documents accessibles
# à l'utilisateur connecté.
@router.get("")
def lister_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_password_changed)
):
    """
    Retourne les documents actifs appartenant
    aux collections autorisées pour l'utilisateur.
    """

    # Identifier le rôle avant de construire la requête.
    # L'éditeur voit tous les documents des collections actives.
    # L'administrateur et l'employé ne voient que les documents
    # des collections auxquelles ils sont personnellement associés.
    role = db.get(Role, current_user.id_role)

    if role is None:
        raise HTTPException(status_code=403, detail="Rôle utilisateur introuvable.")

    statement = (
        select(Document)
        .join(Collection, Document.id_collection == Collection.id_collection)
        .where(
            Collection.est_active.is_(True),
            Document.est_supprime.is_(False)
        )
    )

    if role.intitule in ("Administrateur", "Employé"):
        statement = statement.join(
            user_collections,
            user_collections.c.id_collection == Collection.id_collection
        ).where(user_collections.c.id_user == current_user.id_user)
    elif role.intitule != "Éditeur":
        raise HTTPException(status_code=403, detail="Accès non autorisé.")

    documents = db.scalars(statement.order_by(Document.id_doc.desc())).all()

    # Construire une réponse avec les métadonnées
    # nécessaires à l'interface React.
    return [
        {
            "id_document": document.id_doc,
            "titre": document.titre,
            "type_fichier": document.type_fichier,
            "taille": document.taille,
            "date_ajout": document.date_ajout,
            "id_collection": document.id_collection
        }
        for document in documents
    ]


# Enregistrer l'ouverture réelle d'un document.
# Cette opération est accessible aux utilisateurs autorisés.
# Les consultations sont conservées dans le journal d'audit.
@router.post("/{id_document}/consulter")
def enregistrer_consultation_document(
    id_document: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_password_changed)
):
    """
    Enregistre la consultation d'un document autorisé
    dans le journal d'audit centralisé de DocuMind.
    """

    # Vérifier que le document existe et n'est pas supprimé.
    document = db.get(Document, id_document)

    if document is None or document.est_supprime:
        raise HTTPException(
            status_code=404,
            detail="Document introuvable."
        )

    # Vérifier que la collection documentaire est active.
    collection = db.get(Collection, document.id_collection)

    if collection is None or not collection.est_active:
        raise HTTPException(
            status_code=404,
            detail="Document introuvable."
        )

    # Vérifier les autorisations de l'utilisateur connecté.
    if not acces_collection_autorise(
        db,
        current_user,
        document.id_collection
    ):
        raise HTTPException(
            status_code=404,
            detail="Document introuvable."
        )

    # Enregistrer la consultation dans le journal d'audit.
    create_independent_audit_event(
        id_user=current_user.id_user,
        action="CONSULTATION_DOCUMENT",
        module="DOCUMENTS",
        statut="SUCCES",
        details=f"id_document={document.id_doc}"
    )

    return {
        "message": "Consultation enregistrée avec succès.",
        "id_document": document.id_doc,
        "titre": document.titre
    }


# Récupérer les derniers documents réellement consultés
# par l'utilisateur connecté.
@router.get("/consultations/recentes")
def obtenir_documents_recents(
    limite: int = 3,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_password_changed)
):
    """
    Retourne les derniers documents distincts consultés,
    uniquement s'ils sont toujours accessibles.
    """

    # Encadrer le nombre de résultats demandés.
    if limite < 1 or limite > 20:
        raise HTTPException(
            status_code=400,
            detail="La limite doit être comprise entre 1 et 20."
        )

    # Lire les consultations réussies de l'utilisateur.
    evenements = db.scalars(
        select(AuditEvent)
        .where(
            AuditEvent.id_user == current_user.id_user,
            AuditEvent.action == "CONSULTATION_DOCUMENT",
            AuditEvent.module == "DOCUMENTS",
            AuditEvent.statut == "SUCCES"
        )
        .order_by(
            AuditEvent.date_event.desc(),
            AuditEvent.id_event.desc()
        )
    ).all()

    documents_recents = []
    documents_vus = set()

    for evenement in evenements:

        # Extraire l'identifiant enregistré dans l'audit.
        try:
            id_document = int(
                evenement.details.removeprefix("id_document=")
            )
        except (AttributeError, ValueError):
            continue

        # Éviter de retourner plusieurs fois le même document.
        if id_document in documents_vus:
            continue

        documents_vus.add(id_document)

        # Vérifier que le document existe toujours.
        document = db.get(Document, id_document)

        if document is None or document.est_supprime:
            continue

        # Vérifier que sa collection est active.
        collection = db.get(Collection, document.id_collection)

        if collection is None or not collection.est_active:
            continue

        # Vérifier les autorisations actuelles.
        if not acces_collection_autorise(
            db, current_user, document.id_collection
        ):
            continue

        documents_recents.append({
            "id_document": document.id_doc,
            "titre": document.titre,
            "type_fichier": document.type_fichier,
            "id_collection": document.id_collection,
            "date_consultation": evenement.date_event
        })

        if len(documents_recents) >= limite:
            break

    return {
        "nombre_resultats": len(documents_recents),
        "documents": documents_recents
    }



# Consulter les informations détaillées d'un document.
# L’accès dépend du rôle et de l’association éventuelle.
@router.get("/{id_document}")
def consulter_document(
    id_document: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_password_changed)
):
    """
    Retourne les métadonnées d'un document actif
    accessible à l'utilisateur connecté.
    """

    # Rechercher le document et vérifier qu'il est actif.
    document = db.get(Document, id_document)

    if document is None or document.est_supprime:
        raise HTTPException(
            status_code=404,
            detail="Document introuvable."
        )

    # Vérifier que sa collection est active.
    collection = db.get(Collection, document.id_collection)

    if collection is None or not collection.est_active:
        raise HTTPException(
            status_code=404,
            detail="Document introuvable."
        )

    # Vérifier les droits d’accès à la collection.
    if not acces_collection_autorise(db, current_user, document.id_collection):
        raise HTTPException(
            status_code=404,
            detail="Document introuvable."
        )

    # Récupérer la version la plus récente du document.
    version = db.scalars(
        select(DocVersion)
        .where(DocVersion.id_doc == document.id_doc)
        .order_by(DocVersion.version_num.desc())
        .limit(1)
    ).first()

    # Retourner uniquement les informations nécessaires.
    return {
        "id_document": document.id_doc,
        "titre": document.titre,
        "type_fichier": document.type_fichier,
        "taille": document.taille,
        "date_ajout": document.date_ajout,
        "id_collection": document.id_collection,
        "derniere_version": (
            {
                "id_version": version.id_version,
                "numero": version.version_num,
                "statut": version.statut
            }
            if version is not None else None
        )
    }


# Télécharger le fichier original d'un document.
# Seuls les utilisateurs autorisés à accéder
# à sa collection peuvent récupérer le fichier.
@router.get("/{id_document}/telecharger")
def telecharger_document(
    id_document: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_password_changed)
):
    """
    Télécharge la dernière version du fichier original
    d'un document actif et accessible.
    """

    # Rechercher le document et vérifier qu'il est actif.
    document = db.get(Document, id_document)

    if document is None or document.est_supprime:
        raise HTTPException(
            status_code=404,
            detail="Document introuvable."
        )

    # Vérifier que la collection est active.
    collection = db.get(Collection, document.id_collection)

    if collection is None or not collection.est_active:
        raise HTTPException(
            status_code=404,
            detail="Document introuvable."
        )

    # Vérifier les droits d'accès à la collection.
    if not acces_collection_autorise(db, current_user, document.id_collection):
        raise HTTPException(
            status_code=404,
            detail="Document introuvable."
        )

    # Récupérer la dernière version enregistrée.
    version = db.scalars(
        select(DocVersion)
        .where(DocVersion.id_doc == document.id_doc)
        .order_by(DocVersion.version_num.desc())
        .limit(1)
    ).first()

    if version is None:
        raise HTTPException(
            status_code=404,
            detail="Aucune version disponible."
        )

    # Associer chaque format à son type MIME.
    types_mime = {
        "pdf": "application/pdf",
        "docx": (
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        "txt": "text/plain"
    }

    type_mime = types_mime.get(
        document.type_fichier.lower(),
        "application/octet-stream"
    )

    # Préparer un nom de fichier compatible
    # avec les en-têtes HTTP.
    nom_fichier = document.titre
    nom_encode = quote(nom_fichier, safe="")

    # Retourner les octets du fichier original.
    return StreamingResponse(
        BytesIO(version.contenu),
        media_type=type_mime,
        headers={
            "Content-Disposition": (
                f"attachment; filename*=UTF-8''{nom_encode}"
            ),
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store"
        }
    )


# Ajouter une nouvelle version d'un document existant.
# Les anciennes versions sont conservées dans MySQL.
@router.post("/{id_document}/versions", status_code=201)
async def ajouter_version_document(
    id_document: int,
    fichier: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_editor)
):
    """
    Ajoute une nouvelle version du document.
    L'indexation sera lancée séparément.
    """

    try:
        # Vérifier que le document existe et n'est pas supprimé.
        document = db.get(Document, id_document)

        if document is None or document.est_supprime:
            raise HTTPException(
                status_code=404,
                detail="Document introuvable."
            )

        # Vérifier que la collection est active.
        collection = db.get(Collection, document.id_collection)

        if collection is None or not collection.est_active:
            raise HTTPException(
                status_code=404,
                detail="Collection introuvable ou inactive."
            )

        # Vérifier les droits d'accès à la collection.
        if not acces_collection_autorise(db, current_user, document.id_collection):
            raise HTTPException(
                status_code=403,
                detail="Vous n'avez pas accès à cette collection."
            )

        # Vérifier le nouveau fichier et récupérer ses octets.
        donnees = await preparer_document(fichier)

        # Conserver le même format pour toutes les versions.
        if donnees["type_fichier"] != document.type_fichier.lower():
            raise HTTPException(
                status_code=400,
                detail="Le format doit être identique à celui du document."
            )

        # Verrouiller le document pour éviter que deux ajouts
        # simultanés créent le même numéro de version.
        db.execute(
            select(Document.id_doc)
            .where(Document.id_doc == id_document)
            .with_for_update()
        ).first()

        # Rechercher la dernière version existante.
        derniere_version = db.scalars(
            select(DocVersion)
            .where(DocVersion.id_doc == id_document)
            .order_by(DocVersion.version_num.desc())
            .limit(1)
        ).first()

        numero_version = (
            derniere_version.version_num + 1
            if derniere_version is not None
            else 1
        )

        # Enregistrer la nouvelle version.
        nouvelle_version = DocVersion(
            id_doc=id_document,
            version_num=numero_version,
            statut="pending",
            contenu=donnees["contenu"],
            digest=donnees["digest"]
        )

        db.add(nouvelle_version)
        db.flush()

        # Actualiser les métadonnées du document.
        document.taille = donnees["taille"]

        resultat = {
            "message": "Nouvelle version ajoutée avec succès.",
            "id_document": document.id_doc,
            "id_version": nouvelle_version.id_version,
            "numero_version": nouvelle_version.version_num,
            "statut": nouvelle_version.statut
        }

        db.commit()
        return resultat

    except Exception:
        # Annuler les modifications en cas d'erreur.
        db.rollback()
        raise

    finally:
        # Fermer le fichier importé.
        await fichier.close()
