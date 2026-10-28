# Framecraft Thumbnail Generator

Framecraft Studio is a production-ready, full-stack AI web application that transforms user-uploaded reference photos into stylized, typography-driven social media thumbnails[cite: 1]. Built with a **React (Vite)** frontend and a **FastAPI** backend, it integrates **Supabase Auth**, **Supabase PostgreSQL** (via SQLAlchemy 2.0), **ImageKit CDN**, and **OpenAI (`gpt-image-1-mini`)**[cite: 1], fully containerized with **Docker, Nginx, and Docker Compose** for cloud deployment on **AWS EC2**.

---

## System Architecture 

```mermaid
flowchart TB
    subgraph Client["Browser Client"]
        UI["React + Vite SPA"]
    end

    subgraph EC2["AWS EC2 Instance (Docker Compose Network)"]
        direction TB
        Nginx["Nginx Reverse Proxy & Static Server<br/>(Port 80 | 10MB Upload Limit | 190s Timeout)"]
        FastAPI["FastAPI + Uvicorn Backend<br/>(Port 8000 | Python 3.12)"]
        Pillow["Pillow (PIL) Image Sanitizer<br/>(EXIF Fix, RGB, <=2048px, <=8MB)"]
        Pydantic["Pydantic v2 Validator & Serializer"]
        SQLA["SQLAlchemy 2.0 ORM (psycopg v3)"]
    end

    subgraph External["External Cloud Services"]
        SupabaseAuth["Supabase Auth REST API<br/>(/auth/v1/signup, /token, /user)"]
        SupabaseDB[("Supabase PostgreSQL<br/>(creations & generated_images)")]
        ImageKit["ImageKit.io CDN<br/>(Reference & Output Storage)"]
        OpenAI["OpenAI Images Edit API<br/>(gpt-image-1-mini)"]
    end

    UI -- "HTTP Port 80 (Static Assets)" --> Nginx
    UI -- "HTTP /api/* + HttpOnly Cookies (fc_access, fc_refresh)" --> Nginx
    Nginx -- "Proxy Pass http://backend:8000/api/" --> FastAPI
    FastAPI --> Pydantic
    FastAPI --> Pillow
    FastAPI --> SQLA
    FastAPI -- "HTTPS REST (apikey + Bearer JWT)" --> SupabaseAuth
    SQLA -- "TCP Port 5432 (Connection Pool)" --> SupabaseDB
    FastAPI -- "HTTPS Multipart Upload" --> ImageKit
    FastAPI -- "HTTPS Image Edit (Reference + Style Prompt)" --> OpenAI
```

---

## End-to-End Thumbnail Generation Flow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Nginx as Nginx (Port 80)
    participant API as FastAPI (/api/creations)
    participant SupaAuth as Supabase Auth
    participant PIL as Pillow & Pydantic
    participant IK as ImageKit CDN
    participant DB as Supabase PostgreSQL
    participant AI as OpenAI (gpt-image-1-mini)

    User->>Nginx: POST /api/creations (FormData: image + options JSON)
    Nginx->>API: Forward request + HttpOnly Cookies (fc_access, fc_refresh)
    API->>SupaAuth: GET /auth/v1/user (Verify access token or auto-refresh)
    SupaAuth-->>API: Verified User {id, email}
    API->>PIL: Validate CreationOptions JSON & sanitize image bytes (<=8MB, RGB, <=2048px)
    PIL-->>API: Clean JPEG Bytes
    API->>IK: Upload sanitized reference photo (/framecraft/{user_id}/references)
    IK-->>API: Return (reference_url, reference_file_id)
    API->>DB: INSERT parent Creation row & COMMIT

    loop For each selected style (bold, minimal, vibrant)
        API->>AI: client.images.edit(reference.jpg, style_prompt, size, quality, format)
        alt Generation & Upload Succeeds
            AI-->>API: Base64 Image Data (b64_json)
            API->>IK: Upload generated image (/framecraft/{user_id}/{creation_id})
            IK-->>API: Return (image_url, imagekit_file_id)
            API->>DB: INSERT GeneratedImage (status='success') & COMMIT
        else Provider Failure
            AI-->>API: Error
            API->>DB: INSERT GeneratedImage (status='failed', error_message) & COMMIT
        end
    end

    API->>DB: SELECT Creation with selectinload(Creation.images)
    DB-->>API: Complete Creation + GeneratedImages
    API-->>Nginx: 200 OK (CreationResult JSON)
    Nginx-->>User: Render Generated Thumbnails
```

---

## Database Schema (Entity-Relationship Diagram)

```mermaid
erDiagram
    CREATIONS ||--o{ GENERATED_IMAGES : "has up to 3 styles (CASCADE)"
    CREATIONS {
        string id PK "UUID v4 (String 36)"
        uuid user_id "Indexed - Verified Supabase User UUID"
        text prompt "Main subject description (5-1500 chars)"
        string headline "Main overlay text (max 140 chars)"
        string subtitle "Supporting text (max 200 chars)"
        text extra_prompt "Additional instructions (max 1000 chars)"
        string image_size "1536x1024 | 1024x1024 | 1024x1536"
        string quality "low | medium | high"
        string output_format "jpeg | png | webp"
        string model_name "gpt-image-1-mini"
        text reference_url "ImageKit CDN URL"
        string reference_file_id "ImageKit File ID"
        datetime created_at "UTC Timestamp"
    }
    GENERATED_IMAGES {
        string id PK "UUID v4 (String 36)"
        string creation_id FK "Indexed -> creations.id (ON DELETE CASCADE)"
        string style_name "bold | minimal | vibrant"
        text image_url "Nullable ImageKit CDN URL"
        string imagekit_file_id "Nullable ImageKit File ID"
        string status "success | failed"
        string error_message "Nullable safe error string"
        datetime created_at "UTC Timestamp"
    }
```

---

## Key Features

- **Zero-LocalStorage Cookie Authentication:** Uses Supabase Auth REST endpoints (`signup`, `token`, `user`) with `HttpOnly`, `SameSite=Lax` cookies (`fc_access` and `fc_refresh`) and automatic silent token refresh[cite: 1].
- **Strict Pre-Flight Validation:** Validates all prompt parameters via **Pydantic v2** and sanitizes uploaded images using **Pillow (PIL)** (enforcing an 8 MB file size limit, 25 MP resolution cap against decompression bombs, EXIF rotation normalization, RGB conversion, and `2048x2048` bounding-box scaling) *before* making paid API calls[cite: 1].
- **Multi-Style AI Generation:** Supports three curated design presets (`bold`, `minimal`, `vibrant`) with customizable headlines, subtitles, aspect ratios (`1536x1024`, `1024x1024`, `1024x1536`), quality levels (`low`, `medium`, `high`), and formats (`jpeg`, `png`, `webp`)[cite: 1].
- **Cloud Asset Persistence:** Uploads both original reference photos and AI-generated outputs directly to **ImageKit CDN**, storing the public URL and `fileId` in PostgreSQL[cite: 1].
- **Fault-Tolerant Per-Style Commits:** Saves the parent `Creation` record first and processes each requested style independently so partial successes are preserved even if one style fails[cite: 1].
- **Containerized Multi-Stage Deployment:** Multi-stage Node 20 -> Nginx Alpine frontend build paired with a Python 3.12 Slim backend container, orchestrated via Docker Compose.

---

## Project Directory Structure

```text
thumbnail-studio/
├── backend/
│   ├── app/
│   │   ├── __init__.py      # Backend package marker
│   │   ├── auth.py          # Supabase Auth REST client & HttpOnly cookie logic
│   │   ├── config.py        # Environment variable loader & validation
│   │   ├── database.py      # SQLAlchemy 2.0 ORM models (Creation, GeneratedImage)
│   │   ├── main.py          # FastAPI routes, CORS, & exception handlers
│   │   ├── media.py         # Pillow sanitization, ImageKit upload, & OpenAI image edit
│   │   ├── schemas.py       # Pydantic v2 request/response schemas
│   │   └── styles.py        # Visual style presets (bold, minimal, vibrant)
│   ├── requirements.txt
│   ├── .dockerignore
│   └── Dockerfile
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── nginx.conf           # Production reverse proxy (/api/ -> backend:8000)
│   ├── .dockerignore
│   └── Dockerfile           # Multi-stage React build -> Nginx Alpine
├── docker-compose.yml       # Container orchestration for local build & EC2 runtime
└── README.md
```

---

## API Reference

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | No | Health check returning API status and active OpenAI model (`gpt-image-1-mini`)[cite: 1] |
| `GET` | `/api/styles` | No | Returns available visual style presets (`bold`, `minimal`, `vibrant`)[cite: 1] |
| `POST` | `/api/auth/signup` | No | Registers a new user via Supabase Auth[cite: 1] |
| `POST` | `/api/auth/login` | No | Authenticates user and sets `fc_access` & `fc_refresh` cookies[cite: 1] |
| `GET` | `/api/auth/me` | Yes | Verifies active session and auto-refreshes expired access tokens[cite: 1] |
| `POST` | `/api/auth/logout` | No | Clears `fc_access` and `fc_refresh` cookies[cite: 1] |
| `GET` | `/api/creations` | Yes | Lists up to 50 recent creations owned by the authenticated user[cite: 1] |
| `GET` | `/api/creations/{id}` | Yes | Retrieves a specific creation and its generated images (user-scoped)[cite: 1] |
| `POST` | `/api/creations` | Yes | Validates image, uploads reference to ImageKit, runs OpenAI edits, and saves results[cite: 1] |

---

## Environment Configuration

Create `backend/.env` with the following keys[cite: 1]:

```env
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
IMAGEKIT_PRIVATE_KEY=private_...
IMAGEKIT_URL_ENDPOINT=[https://ik.imagekit.io/your_id](https://ik.imagekit.io/your_id)
OPENAI_API_KEY=sk-proj-...
IMAGE_MODEL=gpt-image-1-mini
COOKIE_SECURE=false
```

Create `frontend/.env`:
```env
# Leave blank so the browser makes relative /api requests proxied by Vite (local) or Nginx (production)
VITE_API_BASE_URL=
```

---

## Running Locally & Deploying to AWS EC2

### 1. Run Locally with Docker Compose
```bash
docker compose build
docker compose up -d
```
- **Web App:** `http://localhost`
- **Health Endpoint:** `http://localhost/api/health`

### 2. Push to Docker Hub & Deploy on AWS EC2
```bash
# On local machine:
docker login
docker compose build
docker compose push

# On AWS EC2 (with Port 80 open in Security Group):
mkdir -p ~/framecraft && cd ~/framecraft
# Create .env and docker-compose.yml, then run:
docker compose pull
docker compose up -d
```
