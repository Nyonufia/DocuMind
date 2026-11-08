# Schéma de validation des informations nécessaires
# à la création d'un utilisateur par un administrateur.

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel): # définit la structure des données envoyées à FastAPI
    nom: str = Field(min_length=2, max_length=100)
    prenom: str = Field(min_length=2, max_length=100)
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    id_role: int = Field(gt=0)
