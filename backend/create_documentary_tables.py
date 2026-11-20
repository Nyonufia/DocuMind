# Création des tables documentaires et RAG de DocuMind.
# Les tables existantes et leurs données sont conservées.

from sqlalchemy import inspect

from app.database import Base, engine
import app.models


def create_documentary_tables():
    # Liste des nouvelles tables à créer
    table_names = [
        "documents",
        "doc_versions",
        "chunks",
        "embeddings",
        "queries",
        "retrieved_chunks",
        "answers",
        "feedbacks",
    ]

    # Vérifier les tables déjà présentes dans MySQL
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    # Sélectionner uniquement les tables manquantes
    missing_tables = [
        Base.metadata.tables[name]
        for name in table_names
        if name not in existing_tables
    ]

    if not missing_tables:
        print("Toutes les tables documentaires existent déjà.")
        return

    # Créer les tables manquantes dans l'ordre
    # imposé par leurs dépendances SQLAlchemy
    Base.metadata.create_all(
        bind=engine,
        tables=missing_tables,
        checkfirst=True
    )

    print("Tables documentaires créées avec succès !")


if __name__ == "__main__":
    create_documentary_tables()
