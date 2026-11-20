# Service de génération des embeddings avec Ollama.
# Les documents sont traités localement, sans API d'IA externe.

import json
import math
from urllib.error import URLError, HTTPError
from urllib.request import Request, build_opener, ProxyHandler

from fastapi import HTTPException


# Configuration du serveur Ollama et du modèle d'embeddings.
OLLAMA_URL = "http://127.0.0.1:11434"
EMBEDDING_MODEL = "nomic-embed-text"

# Désactivation des proxys pour les communications locales.
opener = build_opener(ProxyHandler({}))


def generer_embeddings(textes: list[str]) -> list[list[float]]:
    """
    Génère un vecteur numérique pour chaque texte fourni.
    Utilise l'API locale d'Ollama.
    """

    if not textes:
        return []

    if any(not isinstance(texte, str) or not texte.strip() for texte in textes):
        raise HTTPException(
            status_code=422,
            detail="Les textes à vectoriser doivent être non vides."
        )

    # Préparation de la requête envoyée à Ollama.
    donnees = {
        "model": EMBEDDING_MODEL,
        "input": textes
    }

    requete = Request(
        url=f"{OLLAMA_URL}/api/embed",
        data=json.dumps(donnees).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    # Appel au modèle d'embeddings local.
    try:
        with opener.open(requete, timeout=180) as reponse:
            resultat = json.load(reponse)

    except (URLError, HTTPError, TimeoutError, OSError, ValueError) as erreur:
        raise HTTPException(
            status_code=503,
            detail="Ollama est indisponible ou le modèle d'embeddings ne répond pas."
        ) from erreur

    vecteurs = resultat.get("embeddings")

    # Vérification de la réponse avant tout enregistrement en base.
    if (
        not isinstance(vecteurs, list)
        or len(vecteurs) != len(textes)
        or any(
            not isinstance(vecteur, list)
            or not vecteur
            or any(
                type(valeur) not in (int, float)
                or not math.isfinite(valeur)
                for valeur in vecteur
            )
            for vecteur in vecteurs
        )
    ):
        raise HTTPException(
            status_code=503,
            detail="Ollama a retourné des embeddings invalides."
        )

    return vecteurs
