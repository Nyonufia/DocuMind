
# Schémas de validation des données d'authentification.
# Pydantic vérifie les informations reçues par l'API.

from pydantic import BaseModel, Field


class ChangePasswordRequest(BaseModel):
    ancien_password: str
    nouveau_password: str = Field(min_length=6)
    confirmation_password: str
