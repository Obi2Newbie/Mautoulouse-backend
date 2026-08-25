# Mautoulouse API — FastAPI Backend

## Stack
- **FastAPI** + **Uvicorn** (ASGI server)
- **Supabase Python Client** (database + auth)
- **Pydantic v2** (validation + serialisation)
- **python-jose** (JWT validation)

## Setup

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Fill in your Supabase credentials in .env

# 4. Run dev server
uvicorn app.main:app --reload --port 8000
```

## Endpoints

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| POST | `/auth/signup` | Public | Inscription |
| POST | `/auth/login` | Public | Connexion → JWT |
| GET | `/auth/me` | 🔐 User | Profil courant |
| PATCH | `/auth/me` | 🔐 User | Modifier profil |
| DELETE | `/auth/me` | 🔐 User | Supprimer compte |
| GET | `/events` | Public | Liste événements |
| GET | `/events/{id}` | Public | Détail événement |
| POST | `/events` | 👑 Admin | Créer événement |
| PUT | `/events/{id}` | 👑 Admin | Modifier événement |
| DELETE | `/events/{id}` | 👑 Admin | Supprimer événement |
| POST | `/events/{id}/cover` | 👑 Admin | Upload image couverture |
| GET | `/events/{id}/cover` | Public | Récupérer image couverture |
| POST | `/events/{id}/attend` | 🔐 User | S'inscrire à un événement |
| DELETE | `/events/{id}/attend` | 🔐 User | Annuler inscription |
| GET | `/events/{id}/attendees` | 🔐 User | Liste participants |
| GET | `/questions` | Public | Liste questions |
| GET | `/questions/{id}` | Public | Détail question |
| POST | `/questions` | 🔐 User | Poser une question |
| PUT | `/questions/{id}` | 🔐 Author/Mod | Modifier question |
| DELETE | `/questions/{id}` | 🔐 Author/Admin | Supprimer question |
| POST | `/questions/{id}/vote` | 🔐 User | Voter |
| GET | `/answers/question/{id}` | Public | Réponses threadées |
| POST | `/answers` | 🔐 User | Répondre |
| PUT | `/answers/{id}` | 🔐 Author/Mod | Modifier réponse |
| DELETE | `/answers/{id}` | 🔐 Author/Admin | Supprimer réponse |
| POST | `/answers/{id}/accept` | 🔐 Author | Accepter réponse |
| POST | `/answers/{id}/vote` | 🔐 User | Voter réponse |
| GET | `/albums` | Public | Liste albums |
| POST | `/albums` | 👑 Admin | Créer album |
| GET | `/albums/{id}/photos` | 🔐 User | Photos (métadonnées) |
| GET | `/albums/{id}/photos/{pid}` | 🔐 User | Photo + base64 |
| POST | `/albums/{id}/photos` | 👑 Admin | Upload photo |
| DELETE | `/albums/{id}/photos/{pid}` | 👑 Admin | Supprimer photo |
| GET | `/faqs` | Public | FAQs publiées |
| GET | `/faqs/all` | 👑 Admin | Toutes les FAQs |
| POST | `/faqs` | 👑 Admin | Créer FAQ |
| PUT | `/faqs/{id}` | 👑 Admin | Modifier FAQ |
| DELETE | `/faqs/{id}` | 👑 Admin | Supprimer FAQ |
| GET | `/admin/analytics` | 👑 Admin | Statistiques dashboard |
| GET | `/admin/users` | 👑 Admin | Liste utilisateurs |
| PATCH | `/admin/users/{id}/role` | 👑 Admin | Changer rôle |
| DELETE | `/admin/users/{id}` | 👑 Admin | Supprimer utilisateur |

## Interactive docs
Once running: **http://localhost:8000/docs** (Swagger UI)

## Project structure
```
app/
  main.py          # FastAPI app + CORS + routers
  config.py        # Settings (from .env)
  database.py      # Supabase client factory
  dependencies.py  # Auth dependencies (get_current_user, require_admin…)
  models/
    user.py        # User schemas
    event.py       # Event schemas
    question.py    # Question schemas
    answer.py      # Answer schemas
    photo.py       # Photo + Album + FAQ schemas
  routers/
    auth.py        # /auth/*
    events.py      # /events/*
    questions.py   # /questions/*
    answers.py     # /answers/*
    photos.py      # /albums/*
    faqs.py        # /faqs/*
    admin.py       # /admin/*
```
