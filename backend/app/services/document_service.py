import hashlib
from pathlib import Path

from fastapi import HTTPException, UploadFile


# Extensions autorisées pour l'importation
EXTENSIONS_AUTORISEES = {".pdf", ".docx", ".txt"}

# Taille maximale : 20 Mo
TAILLE_MAX = 20 * 1024 * 1024


async def preparer_document(fichier: UploadFile):
    """
    Vérifie un fichier importé et prépare ses métadonnées.
    Aucune écriture en base de données à cette étape.
    """

    # Vérifier le nom et l'extension du fichier
    nom_fichier = Path(fichier.filename or "").name
    extension = Path(nom_fichier).suffix.lower()

    if not nom_fichier or extension not in EXTENSIONS_AUTORISEES:
        raise HTTPException(
            status_code=400,
            detail="Format non autorisé. Formats acceptés : PDF, DOCX, TXT."
        )

    # Lire au maximum la taille autorisée + 1 octet
    # pour détecter les fichiers trop volumineux
    contenu = await fichier.read(TAILLE_MAX + 1)

    if not contenu:
        raise HTTPException(
            status_code=400,
            detail="Le fichier est vide."
        )

    if len(contenu) > TAILLE_MAX:
        raise HTTPException(
            status_code=413,
            detail="Le fichier dépasse la limite de 20 Mo."
        )

    # Calculer l'empreinte du fichier
    empreinte = hashlib.sha256(contenu).hexdigest()

    return {
        "nom_fichier": nom_fichier,
        "type_fichier": extension.lstrip("."),
        "taille": len(contenu),
        "digest": empreinte,
        "contenu": contenu
    }
