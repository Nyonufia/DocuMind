# Test du service de génération de réponses DocuMind.
# Nous utilisons un passage documentaire connu
# pour vérifier la génération avec citations.

from app.services.generation_service import generer_reponse


# Question à poser à l'assistant.
question = "Qu'est-ce que DocuMind et à quoi sert-il ?"

#question = "Quel est le budget total de développement de DocuMind ?"

# Passage extrait de notre document premier_doc.txt.
passages = [
    {
        "id_document": 1,
        "titre_document": "premier_doc.txt",
        "id_chunk": 2,
        "page": None,
        "position": 0,
        "contenu": (
            "DocuMind est un assistant documentaire sécurisé.\n\n"
            "Il permet d'importer des documents et de "
            "rechercher des informations."
        ),
        "score": 0.7275
    }
]


# Générer la réponse avec Qwen 2.5.
reponse = generer_reponse(question, passages)


# Afficher le résultat dans le terminal.
print("\nQUESTION :")
print(question)

print("\nRÉPONSE GÉNÉRÉE :")
print(reponse)
