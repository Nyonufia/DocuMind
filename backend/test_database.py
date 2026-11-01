
from sqlalchemy import text
from app.database import engine

try:
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT DATABASE(), VERSION()")
        )

        database_name, mysql_version = result.one()

        print("Connexion MySQL reussie !")
        print("Base de donnees :", database_name)
        print("Version MySQL :", mysql_version)

except Exception as erreur:
    print("Erreur de connexion MySQL :")
    print(erreur)
