
# Génération sécurisée des mots de passe temporaires.
# Le module secrets utilise un générateur aléatoire
# adapté aux opérations de sécurité.

import secrets
import string


def generate_temporary_password(length: int = 10) -> str:

    if length < 6:
        raise ValueError(
            "Le mot de passe doit contenir au moins 6 caracteres"
        )

    # Définir les catégories de caractères autorisés.
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    symbols = "!@#$%&*?"

    # Garantir au moins un caractère de chaque catégorie.
    characters = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(symbols)
    ]

    alphabet = lowercase + uppercase + digits + symbols

    # Compléter le mot de passe jusqu'à la longueur demandée.
    characters.extend(
        secrets.choice(alphabet)
        for _ in range(length - len(characters))
    )

    # Mélanger les caractères de manière sécurisée.
    secrets.SystemRandom().shuffle(characters)

    return "".join(characters)
