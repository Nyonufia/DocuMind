# Service de vectorisation des chunks documentaires.
# Génère les embeddings avec Ollama et les enregistre dans MySQL.

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.embedding import Embedding
from app.services.embedding_service import (
    generer_embeddings,
    EMBEDDING_MODEL,
)


def vectoriser_version(db: Session, id_version: int) -> int:
    """
    Génère et enregistre les embeddings des chunks
    associés à une version documentaire.
    """

    # Récupération des chunks dans leur ordre d'apparition.
    chunks = db.scalars(
        select(Chunk)
        .where(Chunk.id_version == id_version)
        .order_by(Chunk.position, Chunk.id_chunk)
    ).all()

    if not chunks:
        raise ValueError(
            "Aucun chunk disponible pour cette version."
        )


    nombre_embeddings = 0

    # Génération des embeddings par lots de 16 chunks.
    try:
        for debut in range(0, len(chunks), 16):
            lot = chunks[debut:debut + 16]

            textes = [chunk.content for chunk in lot]
            vecteurs = generer_embeddings(textes)

            # Enregistrer les embeddings de chaque chunk.
            for chunk, vecteur in zip(lot, vecteurs):
                embedding = db.scalar(
                    select(Embedding).where(
                        Embedding.id_chunk == chunk.id_chunk,
                        Embedding.model_name == EMBEDDING_MODEL,
                    )
                )

                if embedding is None:
                    embedding = Embedding(
                        id_chunk=chunk.id_chunk,
                        model_name=EMBEDDING_MODEL,
                        vector_reference=json.dumps(vecteur),
                    )
                    db.add(embedding)
                else:
                    embedding.vector_reference = json.dumps(vecteur)

                nombre_embeddings += 1

        # Préparer les insertions sans valider la transaction.
        # Le commit final sera effectué par indexation_service.py.
        db.flush()

    except Exception:
        db.rollback()
        raise

    return nombre_embeddings
