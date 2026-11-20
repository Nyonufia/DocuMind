import io

from fastapi import HTTPException
from pypdf import PdfReader
from docx import Document as WordDocument


def extraire_texte(contenu: bytes, type_fichier: str) -> list[dict]:
    """
    Extrait le texte d'un document PDF, DOCX ou TXT.

    Retourne une liste de pages ou de sections
    contenant leur numéro et leur texte.
    """

    if not contenu:
        raise HTTPException(
            status_code=400,
            detail="Le fichier est vide."
        )

    type_fichier = type_fichier.lower().lstrip(".")
    sections = []

    try:
        # Extraction du texte des documents PDF
        if type_fichier == "pdf":
            lecteur = PdfReader(io.BytesIO(contenu))

            # Limiter le nombre de pages à traiter
            if len(lecteur.pages) > 200:
                raise HTTPException(
                    status_code=413,
                    detail="Le PDF dépasse la limite de 200 pages."
                )

            for numero, page in enumerate(lecteur.pages, start=1):
                texte = page.extract_text() or ""

                if texte.strip():
                    sections.append({
                        "page_number": numero,
                        "texte": texte.strip()
                    })

        # Extraction du texte des documents Word
        elif type_fichier == "docx":
            document = WordDocument(io.BytesIO(contenu))

            paragraphes = [
                p.text.strip()
                for p in document.paragraphs
                if p.text.strip()
            ]

            if paragraphes:
                sections.append({
                    "page_number": None,
                    "texte": "\n".join(paragraphes)
                })

        # Extraction du texte des fichiers TXT
        elif type_fichier == "txt":
            try:
                texte = contenu.decode("utf-8-sig")
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Le fichier TXT doit être encodé en UTF-8."
                )

            if texte.strip():
                sections.append({
                    "page_number": None,
                    "texte": texte.strip()
                })

        else:
            raise HTTPException(
                status_code=400,
                detail="Format de fichier non pris en charge."
            )

    except HTTPException:
        raise
    except Exception as erreur:
        raise HTTPException(
            status_code=422,
            detail=f"Impossible d'extraire le texte : {type(erreur).__name__}"
        )

    if not sections:
        raise HTTPException(
            status_code=422,
            detail="Aucun texte exploitable trouvé dans le document."
        )

    return sections
