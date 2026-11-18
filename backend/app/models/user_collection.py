# Table d'association entre les utilisateurs
# et les collections documentaires de DocuMind.
# Un utilisateur peut appartenir à plusieurs collections
# et une collection peut contenir plusieurs utilisateurs.

from sqlalchemy import Table, Column, Integer, ForeignKey
from app.database import Base


user_collections = Table(
    "user_collections",
    Base.metadata,

    # Identifiant de l'utilisateur associé.
    Column(
        "id_user",
        Integer,
        ForeignKey("users.id_user"),
        primary_key=True
    ),

    # Identifiant de la collection associée.
    Column(
        "id_collection",
        Integer,
        ForeignKey("collections.id_collection"),
        primary_key=True
    )
)
