
from fastapi import FastAPI
from app.routers.auth import router as auth_router

from app.routers.users import router as users_router

app = FastAPI(
    title="DocuMind API",
    description="API de l'assistant documentaire sécurisé",
    version="0.1.0"
)
app.include_router(auth_router)

# Enregistrement des routes de gestion des utilisateurs.
app.include_router(users_router)

@app.get("/")
def accueil():
    return {
        "application": "DocuMind",
        "message": "Bienvenue sur DocuMind",
        "status": "API opérationnelle"
    }

@app.get("/health")
def health_check():
    return {
        "status": "OK"
    }

