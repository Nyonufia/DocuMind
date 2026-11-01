
from app.database import Base, engine
from app.models import Role, User

print("Création des tables DocuMind...")

Base.metadata.create_all(bind=engine)

print("Tables créées avec succès !")
