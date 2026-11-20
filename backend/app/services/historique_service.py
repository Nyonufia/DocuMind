# Service de gestion de l'historique DocuMind.
# Enregistre les questions, les réponses et leurs sources dans une même transaction.
# Vérifie les droits actuels avant de divulguer une réponse historique.

from sqlalchemy import select, exists
from sqlalchemy.orm import Session

from app.models.query import Query
from app.models.answer import Answer
from app.models.retrieved_chunk import RetrievedChunk
from app.models.document import Document
from app.models.doc_version import DocVersion
from app.models.chunk import Chunk
from app.models.collection import Collection
from app.models.user import User
from app.models.role import Role
from app.models.user_collection import user_collections


def enregistrer_question(db: Session, id_user: int, question: str) -> Query:
    """Prépare une question sans valider définitivement la transaction."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("La question ne peut pas être vide.")

    nouvelle_question = Query(id_user=id_user, question_text=question.strip())
    db.add(nouvelle_question)
    db.flush()
    return nouvelle_question


def enregistrer_reponse(
    db: Session, id_query: int, texte_reponse: str, abstention: bool
) -> Answer:
    """Prépare une réponse sans valider définitivement la transaction."""
    if not isinstance(texte_reponse, str) or not texte_reponse.strip():
        raise ValueError("La réponse ne peut pas être vide.")

    nouvelle_reponse = Answer(
        id_query=id_query,
        answer_text=texte_reponse.strip(),
        abstained=abstention,
    )
    db.add(nouvelle_reponse)
    db.flush()
    return nouvelle_reponse


def enregistrer_passages(db: Session, id_query: int, passages: list[dict]) -> int:
    """Prépare les associations des passages, sans commit."""
    chunks_vus = set()

    for rang, passage in enumerate(passages, start=1):
        id_chunk = passage["id_chunk"]
        if id_chunk in chunks_vus:
            raise ValueError("Un même chunk ne peut pas être enregistré deux fois.")
        chunks_vus.add(id_chunk)

        db.add(
            RetrievedChunk(
                id_query=id_query,
                id_chunk=id_chunk,
                score=passage["score"],
                rang=rang,
            )
        )

    db.flush()
    return len(passages)


def _role_actif(db: Session, id_user: int) -> str | None:
    """Lit le rôle en base et refuse les comptes inactifs ou rôles inconnus."""
    utilisateur = db.get(User, id_user)
    if utilisateur is None or not utilisateur.est_actif:
        return None

    role = db.get(Role, utilisateur.id_role)
    if role is None or role.intitule not in ("Administrateur", "Éditeur", "Employé"):
        return None
    return role.intitule


def _historique_revoque(id_query: int) -> dict:
    """Réponse minimale, sans question ni texte potentiellement confidentiel."""
    return {
        "id_query": id_query,
        "acces_revoque": True,
        "message": (
            "Cette réponse ne peut plus être consultée "
            "car les autorisations documentaires ont changé."
        ),
    }


def consulter_historique(
    db: Session, id_user: int, limite: int = 20
) -> list[dict]:
    """Liste l'historique personnel en masquant les réponses non autorisées."""
    if not isinstance(limite, int) or not 1 <= limite <= 100:
        raise ValueError("La limite doit être comprise entre 1 et 100.")

    # Un compte désactivé ne doit pas accéder à ses anciennes réponses.
    if _role_actif(db, id_user) is None:
        return []

    identifiants = db.scalars(
        select(Query.id_query)
        .where(Query.id_user == id_user)
        .order_by(Query.date_query.desc(), Query.id_query.desc())
        .limit(limite)
    ).all()

    historique = []
    for id_query in identifiants:
        detail = consulter_detail_historique(db, id_user, id_query)
        if detail is None:
            continue
        if detail.get("acces_revoque"):
            historique.append({
                "id_query": id_query,
                "acces_revoque": True,
                "message": "Cette réponse n'est plus accessible.",
            })
        else:
            historique.append({
                "id_query": detail["id_query"],
                "id_answer": detail["id_answer"],
                "question": detail["question"],
                "reponse": detail["reponse"],
                "abstention": detail["abstention"],
                "date_question": detail["date_question"],
                "acces_revoque": False,
            })
    return historique


def consulter_detail_historique(
    db: Session, id_user: int, id_query: int
) -> dict | None:
    """Consulte une réponse personnelle seulement si toutes ses sources sont autorisées."""
    # Vérifier d'abord l'appartenance de la question à l'utilisateur.
    resultat = db.execute(
        select(Query, Answer)
        .join(Answer, Answer.id_query == Query.id_query)
        .where(Query.id_query == id_query, Query.id_user == id_user)
    ).first()
    if resultat is None:
        return None

    question, reponse = resultat

    # Ne jamais divulguer d'anciennes réponses à un compte désactivé.
    role = _role_actif(db, id_user)
    if role is None:
        return _historique_revoque(id_query)

    # Conserver la liste complète des passages historiques : elle sert à
    # vérifier qu'aucune source ne disparaît du résultat autorisé.
    passages_enregistres = db.scalars(
        select(RetrievedChunk)
        .where(RetrievedChunk.id_query == id_query)
        .order_by(RetrievedChunk.rang)
    ).all()

    # Requête commune : les collections doivent être actives et les documents
    # ne doivent pas avoir été supprimés. Les versions historiques restent
    # consultables si leur document et leur collection sont encore autorisés.
    requete = (
        select(RetrievedChunk, Chunk, Document)
        .join(Chunk, RetrievedChunk.id_chunk == Chunk.id_chunk)
        .join(DocVersion, Chunk.id_version == DocVersion.id_version)
        .join(Document, DocVersion.id_doc == Document.id_doc)
        .join(Collection, Document.id_collection == Collection.id_collection)
        .where(
            RetrievedChunk.id_query == id_query,
            Collection.est_active.is_(True),
            Document.est_supprime.is_(False),
        )
    )

    # L'Éditeur accède à toutes les collections actives.
    # L'Administrateur et l'Employé doivent posséder une association actuelle.
    # EXISTS évite les doublons si la table d'association contient des anomalies.
    if role in ("Administrateur", "Employé"):
        association_autorisee = exists(
            select(user_collections.c.id_user).where(
                user_collections.c.id_user == id_user,
                user_collections.c.id_collection == Collection.id_collection,
            )
        )
        requete = requete.where(association_autorisee)

    lignes = db.execute(requete.order_by(RetrievedChunk.rang)).all()

    # Une seule source supprimée, désactivée, absente ou non autorisée
    # suffit à masquer toute la réponse et toutes ses sources.
    if len(lignes) != len(passages_enregistres):
        return _historique_revoque(id_query)

    sources = []
    for passage, chunk, document in lignes:
        sources.append({
            "id_document": document.id_doc,
            "titre_document": document.titre,
            "id_chunk": chunk.id_chunk,
            "page": chunk.page_number,
            "contenu": chunk.content,
            "score": passage.score,
            "rang": passage.rang,
        })

    return {
        "id_query": question.id_query,
        "id_answer": reponse.id_answer,
        "question": question.question_text,
        "reponse": reponse.answer_text,
        "abstention": reponse.abstained,
        "date_question": question.date_query,
        "acces_revoque": False,
        "sources": sources,
    }
