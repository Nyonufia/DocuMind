import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from jwt import InvalidTokenError

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)

if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise RuntimeError(
        "JWT_SECRET_KEY absente ou trop courte dans .env"
    )



# Création d'un jeton JWT contenant l'identifiant utilisateur
# et la version de sécurité de sa session.

def create_access_token(
    user_id: int,
    token_version: int
) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "ver": token_version,
        "iat": now,
        "exp": now + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )



def verify_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "iat", "exp"]}
        )
    except InvalidTokenError:
        return None
