
from getpass import getpass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models import Role, User
from app.security.password import hash_password


def create_admin():
    print("=== Creation d'un administrateur DocuMind ===")

    nom = input("Nom : ").strip()
    prenom = input("Prenom : ").strip()
    username = input("Nom d'utilisateur : ").strip()
    email = input("Email : ").strip()

    password = getpass("Mot de passe : ")
    confirmation = getpass("Confirmer le mot de passe : ")

    if not all([nom, prenom, username, email, password]):
        print("Erreur : tous les champs sont obligatoires.")
        return

    if len(password) < 6:
        print("Erreur : le mot de passe doit contenir au moins 6 caracteres.")
        return

    if password != confirmation:
        print("Erreur : les mots de passe ne correspondent pas.")
        return

    with SessionLocal() as db:
        role_admin = db.scalar(
            select(Role).where(Role.intitule == "Administrateur")
        )

        if role_admin is None:
            print("Erreur : le role Administrateur est introuvable.")
            return

        existing_user = db.scalar(
            select(User).where(
                (User.username == username) | (User.email == email)
            )
        )

        if existing_user is not None:
            print("Erreur : cet utilisateur ou cet email existe deja.")
            return

        admin = User(
            nom=nom,
            prenom=prenom,
            username=username,
            email=email,
            password_hash=hash_password(password),
            est_actif=True,
            id_role=role_admin.id_role
        )

        try:
            db.add(admin)
            db.commit()
            print("Administrateur cree avec succes !")

        except IntegrityError:
            db.rollback()
            print("Erreur : utilisateur ou email deja utilise.")


if __name__ == "__main__":
    create_admin()
