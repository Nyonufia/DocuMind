from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.doc_version import DocVersion
from app.models.chunk import Chunk

from app.services.extraction_service import extraire_texte
from app.services.chunking_service import decouper_texte
from app.services.vectorisation_service import vectoriser_version


def indexer_document(
    db: Session,
    document: Document,
    version: DocVersion
) -> int:
    """
    Extrait le texte d'une version documentaire,
    le découpe en chunks, génère les embeddings
    avec Ollama et enregistre le tout dans MySQL.
    """

    # Vérifier que la version appartient au document.
    if version.id_doc != document.id_doc:
        raise ValueError(
            "Cette version n'appartient pas au document."
        )

    # Éviter de réindexer une version déjà indexée.
    if version.statut == "indexed":
        raise ValueError(
            "Cette version est déjà indexée."
        )

    # Extraire le texte et le découper en passages.
    sections = extraire_texte(
        version.contenu,
        document.type_fichier
    )

    passages = decouper_texte(sections)

    if not passages:
        raise ValueError(
            "Aucun passage exploitable trouvé."
        )

    try:
        # Supprimer les anciens chunks de cette version.
        # Les embeddings associés sont supprimés
        # grâce à la cascade définie dans MySQL.
        db.execute(
            delete(Chunk).where(
                Chunk.id_version == version.id_version
            )
        )

        # Créer les nouveaux chunks.
        for passage in passages:
            chunk = Chunk(
                id_version=version.id_version,
                content=passage["content"],
                page_number=passage["page_number"],
                position=passage["position"]
            )

            db.add(chunk)

        # Envoyer les insertions à MySQL sans les valider.
        # Cela permet de récupérer les ID des chunks.
        db.flush()

        # Générer les embeddings par lots avec Ollama.
        # Le service les ajoute à la transaction en cours.
        nombre_embeddings = vectoriser_version(
            db,
            version.id_version
        )

        # Vérifier que chaque chunk possède un embedding.
        if nombre_embeddings != len(passages):
            raise ValueError(
                "Le nombre d'embeddings ne correspond "
                "pas au nombre de chunks."
            )

        # Marquer l'indexation comme terminée.
        version.statut = "indexed"
        version.erreur_indexation = None

        # Valider les chunks, embeddings et statut ensemble.
        db.commit()

        return len(passages)

    except Exception:
        # Annuler toutes les modifications non validées.
        db.rollback()
        raise
