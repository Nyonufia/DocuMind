def decouper_texte(
    sections: list[dict],
    taille_chunk: int = 1000,
    chevauchement: int = 200
) -> list[dict]:
    """
    Découpe les sections extraites d'un document
    en passages adaptés à la recherche RAG.

    Les tailles sont exprimées en caractères.
    """

    # Vérifier les paramètres de découpage.
    if taille_chunk <= 0:
        raise ValueError(
            "La taille des chunks doit être positive."
        )

    if not 0 <= chevauchement < taille_chunk:
        raise ValueError(
            "Le chevauchement doit être inférieur à la taille du chunk."
        )

    chunks = []
    position = 0

    # Traiter chaque page ou section séparément
    # pour conserver sa provenance.
    for section in sections:
        texte = section["texte"].strip()
        page_number = section.get("page_number")

        if not texte:
            continue

        debut = 0

        while debut < len(texte):
            fin = min(debut + taille_chunk, len(texte))

            # Éviter de couper un mot lorsque cela
            # est possible sans produire un passage trop court.
            if fin < len(texte):
                espace = texte.rfind(
                    " ",
                    debut + taille_chunk // 2,
                    fin
                )

                if espace > debut:
                    fin = espace

            contenu_chunk = texte[debut:fin].strip()

            if contenu_chunk:
                chunks.append({
                    "content": contenu_chunk,
                    "page_number": page_number,
                    "position": position
                })

                position += 1

            if fin >= len(texte):
                break

            # Reculer pour conserver du contexte
            # entre les passages successifs.
            prochain_debut = max(
                debut + 1,
                fin - chevauchement
            )

            debut = prochain_debut

    return chunks
