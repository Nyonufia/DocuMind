
from fastapi import FastAPI
from app.routers.auth import router as auth_router
from app.routers.audit import router as audit_router
from app.routers.users import router as users_router
from fastapi.middleware.cors import CORSMiddleware
from app.routers import documents

from app.routers.collections import router as collections_router
from app.routers import recherche
from app.routers import feedback


app = FastAPI(
    title="DocuMind API",
    description="API de l'assistant documentaire sécurisé",
    version="0.1.0"
)

""" Autoriser notre frontend React à communiquer avec FastAPI.
Seules les origines locales utilisées pour le développement
 sont autorisées."""

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"]
)

app.include_router(auth_router)

# Enregistrement des routes de gestion des utilisateurs.
app.include_router(users_router)
# Ajouter les routes de consultation du journal d'audit.
app.include_router(audit_router)
# Enregistrement des routes de gestion des collections documentaires.
app.include_router(collections_router)

app.include_router(documents.router)
app.include_router(recherche.router)
app.include_router(feedback.router)
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

