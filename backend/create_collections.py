from sqlalchemy import inspect

from app.database import Base, engine
from app.models.collection import Collection


# Script de création de la table collections.
# Il utilise la connexion MySQL déjà configurée
# dans notre fichier app/database.py.


def create_collections_table():

    # Vérifier si la table existe déjà dans MySQL.
    inspector = inspect(engine)

    if inspector.has_table("collections"):
        print("La table 'collections' existe déjà.")
        return

    # Créer uniquement la table associée
    # au modèle Collection, sans modifier les
    # autres tables de notre base de données.
    Collection.__table__.create(
        bind=engine,
        checkfirst=True
    )

    print("La table 'collections' a été créée avec succès.")


# Exécuter le script uniquement lorsqu'il
# est lancé directement depuis le terminal.
if __name__ == "__main__":
    create_collections_table()
