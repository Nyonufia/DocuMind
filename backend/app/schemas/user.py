# Schéma de validation des informations nécessaires
# à la création d'un utilisateur par un administrateur.

from pydantic import BaseModel, EmailStr, Field, ConfigDict, StrictBool
from typing import Optional


class UserCreate(BaseModel): # définit la structure des données envoyées à FastAPI
    nom: str = Field(min_length=2, max_length=100)
    prenom: str = Field(min_length=2, max_length=100)
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    id_role: int = Field(gt=0)


# Schéma de modification des informations d'un utilisateur.
# Tous les champs sont facultatifs pour permettre
# une modification partielle du compte.

class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nom: Optional[str] = Field(default=None, min_length=2, max_length=100)
    prenom: Optional[str] = Field(default=None, min_length=2, max_length=100)
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None

# Schéma de modification du rôle d'un utilisateur.
# L'identifiant doit correspondre à un rôle existant dans MySQL.

class UserRoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_role: int = Field(gt=0)

# Schéma permettant d'activer ou de désactiver un compte.
# Le statut doit obligatoirement être un booléen.
class UserStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    est_actif: StrictBool