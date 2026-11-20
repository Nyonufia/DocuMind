
from app.models.role import Role
from app.models.user import User
from app.models.audit_event import AuditEvent

# Modèles de gestion des collections
from app.models.collection import Collection
from app.models.user_collection import user_collections


# Modèles de gestion documentaire
from app.models.document import Document
from app.models.doc_version import DocVersion
from app.models.chunk import Chunk
from app.models.embedding import Embedding

# Modèles de recherche et de réponses RAG
from app.models.query import Query
from app.models.retrieved_chunk import RetrievedChunk
from app.models.answer import Answer
from app.models.feedback import Feedback
