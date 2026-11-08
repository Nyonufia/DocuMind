
# Création d'un utilisateur de test pour vérifier
# le changement obligatoire du mot de passe.

from sqlalchemy import select

from app.database import SessionLocal
from app.models.user import User
from app.models.role import Role
from app.security.password import hash_password


def create_test_user():
    with SessionLocal() as db:

        # Éviter de créer plusieurs fois le même utilisateur.
        existing_user = db.scalar(
            select(User).where(User.username == "test_employe")
        )

        if existing_user:
            print("Le compte de test existe déjà.")
            return

        # Récupérer le rôle Employé.
        role = db.scalar(
            select(Role).where(Role.intitule == "Employé")
        )

        if role is None:
            print("Le rôle Employé est introuvable.")
            return

        # Créer un compte avec un mot de passe temporaire.
        user = User(
            nom="Test",
            prenom="Employe",
            username="test_employe",
            email="test.employe@example.com",
            password_hash=hash_password("Temporaire2026!"),
            est_actif=True,
            doit_changer_password=True,
            id_role=role.id_role
        )

        db.add(user)
        db.commit()

        print("Utilisateur de test créé avec succès.")


if __name__ == "__main__":
    create_test_user()
