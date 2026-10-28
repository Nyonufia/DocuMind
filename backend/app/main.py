
from fastapi import FastAPI

app = FastAPI(
    title="DocuMind API",
    description="API de l'assistant documentaire sécurisé",
    version="0.1.0"
)

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
