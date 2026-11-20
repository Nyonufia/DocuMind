# Service de recherche documentaire sémantique.
# Calcul de la similarité entre les embeddings des questions et des chunks.

import json
import math

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.doc_version import DocVersion
from app.models.chunk import Chunk
from app.models.embedding import Embedding
from app.models.collection import Collection
from app.models.user import User
from app.models.role import Role
from app.models.user_collection import user_collections

from app.services.embedding_service import EMBEDDING_MODEL, generer_embeddings


def similarite_cosinus(
    vecteur_question: list[float],
    vecteur_chunk: list[float]
) -> float:
    """Calcule la similarité cosinus entre deux vecteurs de même dimension."""

    # Valider les dimensions et les valeurs numériques.
    if (
        not vecteur_question
        or not vecteur_chunk
        or len(vecteur_question) != len(vecteur_chunk)
    ):
        raise ValueError("Les vecteurs doivent avoir les mêmes dimensions.")

    if any(
        type(valeur) not in (int, float) or not math.isfinite(valeur)
        for valeur in vecteur_question + vecteur_chunk
    ):
        raise ValueError("Les vecteurs contiennent des valeurs invalides.")

    # Calculer le produit scalaire et les normes.
    produit_scalaire = sum(
        a * b for a, b in zip(vecteur_question, vecteur_chunk)
    )
    norme_question = math.sqrt(sum(valeur ** 2 for valeur in vecteur_question))
    norme_chunk = math.sqrt(sum(valeur ** 2 for valeur in vecteur_chunk))

    # Éviter une division par zéro.
    if norme_question == 0 or norme_chunk == 0:
        return 0.0

    return produit_scalaire / (norme_question * norme_chunk)


def recuperer_chunks_autorises(db: Session, id_user: int):
    """
    Récupère les chunks de la dernière version indexée de chaque document.

    Éditeur : accès à toutes les collections actives.
    Administrateur et Employé : accès aux collections attribuées uniquement.
    """

    # Identifier le rôle directement en base : ne jamais se fier au rôle
    # communiqué par le frontend.
    utilisateur = db.get(User, id_user)
    if utilisateur is None or not utilisateur.est_actif:
        return []

    role = db.get(Role, utilisateur.id_role)
    if role is None or role.intitule not in (
        "Administrateur", "Éditeur", "Employé"
    ):
        return []

    # Sélectionner la dernière version indexée de chaque document.
    derniere_version_indexee = (
        select(
            DocVersion.id_doc,
            func.max(DocVersion.version_num).label("numero_version")
        )
        .where(DocVersion.statut == "indexed")
        .group_by(DocVersion.id_doc)
        .subquery()
    )

    # Construire la requête de base, en excluant systématiquement les
    # collections inactives et les documents supprimés.
    requete = (
        select(Chunk, Embedding, Document)
        .join(DocVersion, Chunk.id_version == DocVersion.id_version)
        .join(
            derniere_version_indexee,
            (DocVersion.id_doc == derniere_version_indexee.c.id_doc)
            & (
                DocVersion.version_num
                == derniere_version_indexee.c.numero_version
            )
        )
        .join(Document, DocVersion.id_doc == Document.id_doc)
        .join(Collection, Document.id_collection == Collection.id_collection)
        .join(Embedding, Embedding.id_chunk == Chunk.id_chunk)
        .where(
            Collection.est_active.is_(True),
            Document.est_supprime.is_(False),
            DocVersion.statut == "indexed",
            Embedding.model_name == EMBEDDING_MODEL
        )
    )

    # Seuls les éditeurs bénéficient d'un accès global aux collections
    # actives. Les administrateurs et employés doivent être associés.
    if role.intitule in ("Administrateur", "Employé"):
        requete = (
            requete.join(
                user_collections,
                user_collections.c.id_collection == Collection.id_collection
            )
            .where(user_collections.c.id_user == id_user)
        )

    requete = requete.order_by(Document.id_doc, Chunk.position)
    return db.execute(requete).all()


def rechercher_passages(
    db: Session,
    id_user: int,
    question: str,
    limite: int = 5,
    seuil_similarite: float = 0.65
) -> list[dict]:
    """Retourne les passages autorisés classés par similarité décroissante."""

    # Valider la question et les paramètres de recherche.
    if not isinstance(question, str) or not 3 <= len(question.strip()) <= 1500:
        raise ValueError(
            "La question doit contenir entre 3 et 1500 caractères."
        )

    if not isinstance(limite, int) or not 1 <= limite <= 20:
        raise ValueError("La limite doit être comprise entre 1 et 20.")

    if not 0 <= seuil_similarite <= 1:
        raise ValueError("Le seuil de similarité doit être compris entre 0 et 1.")

    question = question.strip()

    # Appliquer les autorisations en base avant de calculer les scores.
    lignes = recuperer_chunks_autorises(db, id_user)
    if not lignes:
        return []

    # Générer l'embedding de la question avec Ollama.
    vecteur_question = generer_embeddings([question])[0]
    resultats = []

    # Comparer uniquement les chunks autorisés.
    for chunk, embedding, document in lignes:
        try:
            vecteur_chunk = json.loads(embedding.vector_reference)
            score = similarite_cosinus(vecteur_question, vecteur_chunk)
        except (ValueError, TypeError):
            # Ignorer les embeddings mal formés.
            continue

        if score < seuil_similarite:
            continue

        resultats.append({
            "id_document": document.id_doc,
            "titre_document": document.titre,
            "id_chunk": chunk.id_chunk,
            "page": chunk.page_number,
            "position": chunk.position,
            "contenu": chunk.content,
            "score": round(score, 4)
        })

    # Classer les résultats du plus pertinent au moins pertinent.
    resultats.sort(
        key=lambda resultat: resultat["score"],
        reverse=True
    )
    return resultats[:limite]
