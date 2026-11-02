# DocuMind — Assistant documentaire sécurisé basé sur le RAG

> **Statut :** projet en développement — phase de conception réalisée et environnement technique initialisé. Les fonctionnalités métier et RAG décrites ci-dessous constituent principalement le périmètre **prévu**, et non des fonctionnalités déjà livrées.

## 1. Présentation du projet

**DocuMind** est un projet académique de développement d'un assistant documentaire sécurisé utilisant une architecture **RAG** (*Retrieval-Augmented Generation*, ou génération augmentée par récupération d'informations).

Il vise à aider les organisations à retrouver des informations dans un ensemble de documents et à poser des questions en langage naturel. L'application doit retrouver les passages pertinents, générer une réponse fondée sur ces passages, **citer ses sources** et **s'abstenir** lorsque les documents disponibles ne permettent pas de répondre de manière fiable.

Le projet comprend également l'authentification, la gestion des rôles, les droits d'accès aux documents, la gestion documentaire, les retours utilisateurs et les fonctions d'administration.

**Cadre :** projet d'intégration en Techniques de l'informatique, réalisé en équipe de trois selon **Scrum**, sur **15 semaines**.

## 2. Objectifs

- Centraliser un corpus documentaire de démonstration.
- Importer et indexer des documents pour faciliter leur recherche.
- Permettre une recherche de passages pertinents et des questions en langage naturel.
- Produire des réponses accompagnées de références aux documents sources.
- Refuser de répondre lorsqu'aucune preuve documentaire suffisante n'est disponible.
- Appliquer les autorisations **avant** la récupération des passages et la génération des réponses.
- Recueillir des feedbacks et fournir des fonctions de suivi et d'administration.
- Déployer une application testable et reproductible, avec documentation et tests.

### Périmètre du MVP attendu

Le cahier des charges prévoit notamment :

- Un corpus de démonstration d'au moins **20 documents** non sensibles.
- L'importation d'au moins **deux formats** parmi PDF, TXT et Markdown.
- Extraction du texte, découpage en segments (*chunks*), indexation et suivi des erreurs.
- Recherche lexicale ou sémantique, idéalement avec embeddings.
- Questions/réponses sourcées, avec abstention si les preuves sont insuffisantes.
- Gestion des utilisateurs, rôles et droits d'accès aux collections/documents.
- Feedback sur la qualité des réponses et évaluation avec au moins **20 questions de référence**.

## 3. Utilisateurs et rôles

| Acteur | Responsabilités prévues |
|---|---|
| **Employé / Utilisateur** | Se connecter, rechercher des informations, poser des questions, consulter les réponses et leurs sources, donner un avis. |
| **Éditeur de contenu** | Importer et gérer les documents, suivre leur indexation et demander leur réindexation. |
| **Administrateur** | Gérer les utilisateurs, rôles et permissions, consulter les erreurs, indicateurs et événements d'audit. |

Les autorisations doivent être vérifiées côté serveur : une interface masquée ne suffit pas à protéger une ressource.

## 4. Technologies et outils

| Domaine | Choix retenu ou envisagé | État |
|---|---|---|
| Frontend | React + TypeScript | Prévu |
| Backend / API | Python + FastAPI | Initialisé |
| Base relationnelle | MySQL Server 8.0 | Base `documind` créée et accessible dans Workbench |
| ORM / pilote MySQL | SQLAlchemy + PyMySQL | Configuration proposée ; connexion applicative à confirmer |
| Variables d'environnement | `python-dotenv` + fichier `.env` | Configuration proposée |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2` envisagé) | Prévu, non intégré |
| Index vectoriel | FAISS ou Chroma | À sélectionner et intégrer |
| Génération de réponses | Modèle local via Ollama (Gemma/Mistral envisagés) ou solution remplaçable | Prévu |
| Authentification | Mots de passe hachés, JWT, RBAC | Prévu |
| Tests | pytest, tests API et évaluation RAG | Prévu |
| Déploiement | Docker / Docker Compose | Prévu |
| Gestion du code | Git et GitHub | Dépôt initial publié |
| Gestion de projet | Jira / Scrum | Backlog et planification travaillés |
| Modélisation et interfaces | UML et Figma | Dossier de conception travaillé |

> Les outils RAG et le modèle de génération ne sont pas encore présentés comme des dépendances installées. Leur choix final sera documenté au moment de l'implémentation.

## 5. Architecture fonctionnelle envisagée

```text
Utilisateur (React + TypeScript)
           |
           v
       API FastAPI
           |
           +--> Authentification / rôles / permissions
           |           |
           |           v
           |         MySQL
           |
           +--> Gestion documentaire
           |       Import -> Extraction -> Chunking -> Embeddings -> Index
           |
           +--> Assistant RAG
                   Question utilisateur
                          |
                          v
                 Vérification des droits
                          |
                          v
                 Recherche des passages
                          |
                          v
                 Génération de la réponse
                          |
                          v
                 Réponse + sources / abstention
```

**Rôles des données :** MySQL conserve les informations structurées (utilisateurs, rôles, documents, versions, questions, réponses, feedback et audit). L'index vectoriel sert à rechercher rapidement les passages proches sémantiquement d'une question. Les fichiers documentaires et les vecteurs ne doivent pas être confondus avec les tables relationnelles.

### Notions centrales du RAG

- **Chunk** : morceau de texte extrait d'un document, par exemple un paragraphe d'une procédure interne.
- **Embedding** : représentation numérique du sens d'un chunk ou d'une question, utilisée pour calculer leur similarité.
- **RetrievedChunk** : association entre une recherche et un chunk retrouvé, avec un score de pertinence et éventuellement un rang.
- **Answer** : réponse produite à partir des passages autorisés et pertinents, avec les références nécessaires.

**Exemple :** si un employé demande « Comment demander un congé ? », DocuMind doit chercher les passages autorisés du guide RH, sélectionner ceux qui décrivent la procédure, puis répondre en citant ce guide. Si aucun passage fiable n'est trouvé, il doit l'indiquer au lieu d'inventer une procédure.

## 6. Conception et modélisation UML

Les travaux de conception comprennent :

- **Diagrammes de cas d'utilisation par acteur** : Employé, Éditeur de contenu et Administrateur.
- **Diagrammes de séquence** : un scénario représentatif choisi pour chaque acteur.
- **Diagramme de classes** : modèle métier pour les utilisateurs, documents, index, requêtes, réponses et traces.
- **Maquettes Figma** : interfaces de l'application, à compléter ou relier dans le dossier de conception.

### Classes conceptuelles proposées

| Classe | Fonction |
|---|---|
| `User` | Identité et état d'un utilisateur. |
| `Role` | Rôle attribué à un utilisateur. |
| `Collection` | Regroupement de documents soumis à des autorisations. |
| `Document` | Métadonnées et état d'un document. |
| `DocumentVersion` | Versions successives d'un document. |
| `Chunk` | Passage extrait d'une version documentaire. |
| `Embedding` | Référence à la représentation vectorielle d'un passage. |
| `Query` | Question posée par un utilisateur. |
| `RetrievedChunk` | Passage retrouvé pour une question, avec pertinence/rang. |
| `Answer` | Réponse et état de génération. |
| `Feedback` | Appréciation d'une réponse par un utilisateur. |
| `AuditEvent` | Trace des opérations importantes. |

Ce modèle reste **conceptuel** : les associations, contraintes et tables de jonction nécessaires aux autorisations seront finalisées avant la création des migrations MySQL.

## 7. Organisation Scrum et Jira

**Durée prévue :** 15 semaines, du **4 septembre au 17 décembre 2026**. L'équipe est composée de trois membres, avec répartition des responsabilités de **Product Owner**, **Scrum Master** et **Développeur**, tout en conservant une contribution technique collective.

### Épics du backlog

| Épic | Périmètre |
|---|---|
| **1. Analyse et conception** | Besoins, architecture, modèle de données, corpus, prototype et stratégie de tests. |
| **2. Utilisateurs et sécurité** | Authentification, rôles, permissions, protection des secrets et validation. |
| **3. Assistant RAG et recherche** | Import, extraction, chunking, indexation, recherche, réponses et citations. |
| **4. Feedback et administration** | Avis, historique, indexation, réindexation, indicateurs et audit. |
| **5. Qualité et mise en production** | Tests, évaluation RAG, sécurité, conteneurisation, CI et livraison. |

Le backlog a été structuré en **User Stories** et sous-tâches, avec priorités, critères d'acceptation, estimations et dépendances à suivre dans Jira.

### Versions planifiées

| Version | Période prévue | Objectif |
|---|---|---|
| **v0.1 — Fondation, conception et sécurité** | 04/09/2026 – 01/10/2026 | Cadrage, architecture, modèle de données et fondations de sécurité. |
| **v0.2 — RAG documentaire sécurisé** | 02/10/2026 – 26/11/2026 | Gestion documentaire, indexation, recherche et assistant RAG sécurisé. |
| **v1.0 — MVP final** | 27/11/2026 – 17/12/2026 | Tests, corrections, documentation et livraison finale. |

Ces dates sont des **objectifs de planification**, pas des preuves de livraison des fonctionnalités.

## 8. Avancement réel du projet

### Réalisé ou montré jusqu'à présent

- [x] Définition du sujet, du contexte, des objectifs et du périmètre de DocuMind.
- [x] Analyse des acteurs, fonctionnalités et exigences de sécurité.
- [x] Travail de conception UML et préparation du dossier de maquettes Figma.
- [x] Élaboration du backlog, des épics, des User Stories et du calendrier Jira.
- [x] Création du dépôt GitHub et premier `push` réussi sur la branche `main`.
- [x] Initialisation du backend Python avec structure `backend/app`.
- [x] Création des fichiers `app/__init__.py`, `app/main.py`, `app/database.py` et `requirements.txt` dans le dépôt initial.
- [x] Mise en place d'une application FastAPI de départ et de routes simples de vérification.
- [x] Installation/récupération de MySQL Server 8.0.46 et résolution du problème de démarrage.
- [x] Récupération de l'accès administrateur MySQL et configuration du service Windows.
- [x] Connexion à MySQL Workbench et création de la base `documind`.
- [x] Préparation des instructions pour connecter SQLAlchemy/PyMySQL à MySQL depuis CMD.
- [x] Définition du format du journal de bord : tâche, détails, date, intervenant.

### À vérifier ou terminer

- [ ] Confirmer par une exécution réussie de `python test_database.py` la connexion **FastAPI/Python ↔ MySQL**.
- [ ] Vérifier le contenu réel et les dépendances actuelles de `database.py` et `requirements.txt`.
- [ ] Créer les modèles SQLAlchemy et migrations pour `User` et `Role`.
- [ ] Implémenter l'authentification, le hachage des mots de passe et les JWT.
- [ ] Développer le contrôle d'accès aux documents et aux fonctionnalités.
- [ ] Développer l'importation, l'extraction, le découpage et l'indexation des documents.
- [ ] Intégrer les embeddings, la recherche vectorielle et la génération sourcée.
- [ ] Développer les interfaces React et les fonctionnalités de feedback/admin.
- [ ] Réaliser les tests, l'évaluation sur 20 questions, la CI et le déploiement Docker.

## 9. Structure du dépôt

Structure initiale **observée sur GitHub** :

```text
DocuMind_dev/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── database.py
│   └── requirements.txt
├── .gitignore
└── .idea/                 # Dossier IDE présent dans le premier commit
```

Structure **cible** au fil du développement :

```text
DocuMind_dev/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── routers/
│   │   ├── services/
│   │   └── security/
│   ├── tests/
│   ├── requirements.txt
│   ├── .env                 # Local, non suivi par Git
│   └── .env.example         # À ajouter, sans secrets
├── frontend/                # À développer
├── documents/               # Corpus de démonstration
├── docker-compose.yml       # Prévu
├── .gitignore
└── README.md
```

> Les dossiers cibles ne sont pas tous nécessairement présents dans le dépôt actuel. Git ne conserve pas les dossiers vides sans fichier suivi.

## 10. Installation locale du backend (Windows CMD)

### Prérequis

- Python 3.13 ou une version compatible avec les dépendances du projet.
- Git.
- MySQL Server 8.0 et MySQL Workbench.
- Un éditeur tel que VS Code.

### Récupérer le projet

```cmd
 git clone https://github.com/Nyonufia/DocuMind.git
 cd DocuMind\backend
```

### Créer et activer un environnement virtuel

```cmd
python -m venv venv
venv\Scripts\activate.bat
```

Si un environnement virtuel existe déjà et fonctionne, active-le simplement. En cas d'erreur `ensurepip`, corriger l'installation Python ou utiliser un chemin d'environnement plus court avant de poursuivre.

### Installer les dépendances

```cmd
python -m pip install -r requirements.txt
```

Si le fichier n'est pas encore à jour, les bibliothèques utilisées pour le backend et la connexion MySQL sont notamment :

```cmd
python -m pip install fastapi "uvicorn[standard]" sqlalchemy pymysql python-dotenv cryptography
python -m pip freeze > requirements.txt
```

### Configurer les variables d'environnement

Créer localement `backend/.env` :

```dotenv
DB_HOST=127.0.0.1
DB_PORT=3307
DB_NAME=documind
DB_USER=documind_app
DB_PASSWORD=REMPLACER_PAR_LE_MOT_DE_PASSE_LOCAL
```

**Important :** `3307` correspond au port MySQL observé pendant la configuration de l'environnement initial. Sur une autre machine, vérifier le port effectif dans Workbench :

```sql
SHOW VARIABLES LIKE 'port';
```

Le compte `documind_app` doit exister et disposer des droits nécessaires sur la base `documind`. Ne pas utiliser `root` pour les connexions de l'application.

### Créer la base MySQL si nécessaire

Dans MySQL Workbench, avec un compte administrateur :

```sql
CREATE DATABASE IF NOT EXISTS documind
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

Si le compte applicatif n'existe pas encore :

```sql
CREATE USER 'documind_app'@'localhost'
IDENTIFIED BY 'CHOISIR_UN_MOT_DE_PASSE_FORT';

GRANT ALL PRIVILEGES ON documind.*
TO 'documind_app'@'localhost';
```

### Vérifier la connexion Python–MySQL

Le test ci-dessous est une **étape prévue à confirmer**, pas un test déjà attesté comme réussi :

```cmd
python test_database.py
```

Si `test_database.py` n'existe pas encore, il doit être créé dans `backend/` pour ouvrir une connexion SQLAlchemy et exécuter `SELECT DATABASE(), VERSION()`.

### Démarrer FastAPI

Depuis le dossier `backend` :

```cmd
python -m uvicorn app.main:app --reload
```

- API : http://127.0.0.1:8000/
- Documentation Swagger : http://127.0.0.1:8000/docs
- Vérification de santé, si la route est conservée : http://127.0.0.1:8000/health

Ces routes concernent la **base initiale de l'API**, et non encore un assistant RAG fonctionnel.

## 11. Sécurité et bonnes pratiques

- Ne jamais publier `.env`, mots de passe, clés d'API ou données sensibles.
- Ajouter `venv/`, `__pycache__/`, `.env` et `.idea/` au `.gitignore` ; retirer du suivi les dossiers IDE déjà ajoutés si nécessaire.
- Conserver un fichier `.env.example` avec des valeurs fictives.
- Utiliser un utilisateur MySQL applicatif distinct de `root`.
- Hacher les mots de passe ; ne jamais les stocker en clair dans la base.
- Valider les entrées et les fichiers téléversés côté serveur.
- Contrôler les droits d'accès **avant** la recherche RAG, afin d'éviter la fuite de documents non autorisés.
- Protéger l'assistant contre les instructions malveillantes présentes dans les documents (prompt injection).
- Utiliser uniquement des documents publics ou de démonstration pendant le projet académique.

## 12. Tests et critères de qualité prévus

- Tests unitaires du backend et des fonctions de traitement documentaire.
- Tests d'intégration API ↔ MySQL ↔ index documentaire.
- Tests négatifs de contrôle d'accès (utilisateur non autorisé).
- Tests de provenance : vérifier que les sources citées soutiennent la réponse.
- Tests d'abstention lorsque le corpus ne contient pas la réponse.
- Jeu d'évaluation d'au moins **20 questions** avec résultats attendus.
- Tests de robustesse : fichiers invalides, erreurs d'indexation, réponses du modèle indisponibles.
- Vérification de l'absence de secrets dans Git et de la reproductibilité de l'installation.

Aucun taux de réussite, couverture de tests ou métrique de performance n'est encore annoncé : ces résultats devront être mesurés.

## 13. Collaboration GitHub

**Dépôt :** https://github.com/Nyonufia/DocuMind

Le premier commit publié portait sur l'**initialisation du projet DocuMind avec FastAPI**. La branche principale est `main`.

Exemple de cycle de travail en CMD :

```cmd
git pull origin main
git status
git add .
git commit -m "Description precise de la modification"
git push origin main
```

Pour le travail en équipe, privilégier des branches de fonctionnalité et des Pull Requests avec revue avant fusion dans `main`.

## 14. Journal de bord

Un journal de bord est prévu pour conserver la trace des travaux effectués et faciliter le suivi de l'équipe.

| Tâche effectuée | Détails | Date | Intervenant |
|---|---|---|-------------|
| Initialisation backend | Structure Python/FastAPI et premiers fichiers | Octobre 2026 |             |
| Publication du dépôt | Initialisation Git et premier push sur GitHub | 28/10/2026 |             |
| Configuration MySQL | Récupération de l'accès, démarrage et service Windows | 30/10/2026 |             |
| Création de la base | Base `documind` créée dans MySQL Workbench | 30/10/2026 |             |
| Préparation de la connexion | Configuration proposée pour SQLAlchemy/PyMySQL et `.env` | 30/10/2026 |             |

Les noms des intervenants et les dates exactes des travaux de conception seront complétés à partir du journal d'équipe.

## 15. Documentation et liens

- **GitHub :** https://github.com/Nyonufia/DocuMind
- **Jira :** 
- **Figma :** 
- **Dossier UML :** 
- **Journal de bord :** 

## 16. Prochaines étapes prioritaires

1. Confirmer l'accès MySQL avec le compte `documind_app` depuis Python (`test_database.py`).
2. Finaliser `database.py`, vérifier les variables d'environnement et enregistrer les dépendances.
3. Implémenter `User` et `Role`, puis créer les migrations de schéma.
4. Ajouter l'authentification sécurisée et les permissions.
5. Développer la gestion des documents et commencer le pipeline d'indexation RAG.
6. Construire les premières interfaces React, puis tester les parcours utilisateurs.

---

**Note de suivi — 1er novembre 2026 :** ce README documente les choix, travaux de conception et initialisations connus à cette date. Il doit être mis à jour après chaque fonctionnalité effectivement implémentée, testée et intégrée.
