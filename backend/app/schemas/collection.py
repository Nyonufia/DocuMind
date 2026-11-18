from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field
)
from typing import Literal

# Schéma de base contenant les informations
# communes à une collection.
class CollectionBase(BaseModel):

    collection_name: str = Field(
        min_length=2,
        max_length=150
    )

    description: str | None = Field(
        default=None,
        max_length=500
    )


    # Le niveau d'accès doit correspondre
    # à l'une des quatre valeurs autorisées.
    niveau_acces: Literal[
        "Public",
        "Interne",
        "Restreint",
        "Confidentiel"
    ]



# Schéma utilisé lors de la création.
# Il reprend les champs obligatoires
# définis dans CollectionBase.
class CollectionCreate(CollectionBase):
    pass


# Schéma utilisé lors d'une modification.
# Tous les champs sont facultatifs afin
# de modifier uniquement les valeurs fournies.
class CollectionUpdate(BaseModel):

    collection_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150
    )

    description: str | None = Field(
        default=None,
        max_length=500
    )


    # Lors d'une modification, le niveau d'accès
    # est facultatif, mais sa valeur reste contrôlée.
    niveau_acces: Literal[
        "Public",
        "Interne",
        "Restreint",
        "Confidentiel"
    ] | None = None


    est_active: bool | None = None


# Schéma définissant les informations
# retournées au frontend React.
class CollectionResponse(CollectionBase):

    id_collection: int

    date_creation: datetime

    est_active: bool

    # Autoriser Pydantic à convertir directement
    # un objet SQLAlchemy en réponse JSON.
    model_config = ConfigDict(
        from_attributes=True
    )
