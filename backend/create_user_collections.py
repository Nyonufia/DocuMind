
# Script de création de la table d'association
# entre les utilisateurs et les collections.
# Les tables existantes ne seront pas modifiées.

from app.database import engine

# Charger les modèles référencés par les clés étrangères.
# Ces imports permettent à SQLAlchemy de connaître
# les tables users et collections.
from app.models.user import User
from app.models.collection import Collection

# Importer la table d'association à créer.
from app.models.user_collection import user_collections


def create_user_collections_table():

    # Créer uniquement la table user_collections.
    # Les tables users et collections restent inchangées.
    user_collections.create(
        bind=engine,
        checkfirst=True
    )

    print(
        "Table user_collections créée ou déjà existante."
    )


# Lancer la création uniquement lorsque
# ce fichier est exécuté directement.
if __name__ == "__main__":
    create_user_collections_table()
