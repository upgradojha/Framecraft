# Framecraft Thumbnail Studio — Final College Project

**Beginner-friendly full stack project.** The original Framecraft dashboard's lime-on-dark visual theme is preserved, with a matching Sign in/Register screen and a per-user creative library.

### Architecture

```text
React (http://localhost:5173)
    │
    ├─ /api/auth/signup/login/me/logout  -> FastAPI -> Supabase Auth
    │                                         │ (HttpOnly cookies)
    └─ /api/creations                   -> FastAPI -> verify Auth token
                                               │
                      ┌────────────────────────┼────────────────────┐
                      ↓                        ↓                    ↓
              Supabase PostgreSQL          ImageKit             OpenAI
              metadata & users             images/CDN        image edits API
                      ↑                        │
                   pgAdmin               Image URLs returned in JSON
```

**No queue, no workers, no status polling, no SSE, no fake demo image generator.** A single authenticated `/api/creations` POST runs up to 3 image requests sequentially and returns their results. If one style fails, it is saved with `failed` status while other styles may still succeed. This approach is easy to discuss in a college viva. Downside: a slow image model keeps the HTTP request open; long reverse-proxy timeouts would require a future architecture change.

### Key files

| File | One simple responsibility |
|---|---|
| `backend/app/main.py` | HTTP routes + generation flow |
| `backend/app/auth.py` | Supabase authentication + safe session cookies |
| `backend/app/database.py` | Two SQLAlchemy data models + PostgreSQL session |
| `backend/app/schemas.py` | Pydantic input/response validation |
| `backend/app/media.py` | Real OpenAI image editing + ImageKit upload |
| `backend/app/styles.py` | Three named style instructions |
| `backend/app/config.py` | Keys + choose image model with `.env` |
| `frontend/src/App.jsx` | Auth screen, personalized dashboard, form, gallery |
| `frontend/src/api.js` | Small wrapper around FastAPI routes |
| `sql/01_schema.sql` | Database tables, indexes, RLS |
| `sql/02_learning_queries.sql` | College viva practice queries |
| `read.md` | Step-by-step setup in Hinglish |
| `CODE_FLOW_HINGLISH.md` | Explain the code and API flow |

### Setup

Follow **[`read.md`](read.md)** exactly. Supabase needs one SQL schema run before starting the app. Copy backend `.env.example` to `.env` and supply account credentials. The frontend only receives JSON and public ImageKit URLs, never server credentials.

### API endpoints

| Method | Path | Purpose | Login needed? |
|---|---|---|---|
| GET | `/api/health` | Check FastAPI and selected model | No |
| GET | `/api/styles` | All selectable presets | No |
| POST | `/api/auth/signup` | Supabase email register | No |
| POST | `/api/auth/login` | Supabase email sign-in | No |
| GET | `/api/auth/me` | Verify session cookie, auto-refresh if possible | Yes |
| POST | `/api/auth/logout` | Clear cookies | No |
| GET | `/api/creations` | Current user's 50 latest creations | Yes |
| GET | `/api/creations/{id}` | Get one owned creation | Yes |
| POST | `/api/creations` | One real image generation request per selected style | Yes |

`POST /api/creations` is `multipart/form-data`:
- `image`: JPEG, PNG, or WebP under 8MB
- `options`: JSON string validated by `CreationOptions`:

```json
{
  "prompt": "A tutorial teaching FastAPI from scratch",
  "headline": "FASTAPI COURSE",
  "subtitle": "Full beginner guide",
  "extra_prompt": "Modern dark tech setup, subject on right",
  "styles": ["bold", "minimal"],
  "image_size": "1536x1024",
  "quality": "low",
  "output_format": "jpeg"
}
```

The image model is intentionally configured **server-side** via `IMAGE_MODEL=gpt-image-1-mini`. To change model, update `.env`, restart backend, and ensure provider supports `images.edit` inputs, formats, sizes and qualities. **GPT-2 is a text-generation model, not an image generator.** Another API provider would need an adapter change in the single `generate_image()` function, since providers have different request/response formats.

### Access control

Supabase Auth manages `auth.users`; application `creations` and `generated_images` are under `public`. The `user_id` foreign key points to `auth.users(id)`. `sql/01_schema.sql` enables row-level security for future direct Supabase Data API use. The FastAPI server uses a privileged PostgreSQL connection, therefore it **always** filters creation reads by the authenticated user's ID. Supabase `/auth/v1/user` validates the HttpOnly access-token cookie and expired sessions may be refreshed with the rotating refresh cookie. Configure `COOKIE_SECURE=true` on HTTPS in production; serve frontend/API from the same site or provide a carefully reviewed cross-site/CSRF configuration.

The generated assets are stored as **ImageKit files**, not PostgreSQL BLOBs; the DB stores image URL, ImageKit file ID and user-specific settings. URLs are public by default: authentication protects the gallery listing, **not** the accessibility of copied ImageKit URLs. Use private files and signed URLs in a future version if private CDN access is required.

### Tests

```bash
cd backend
pip install -r requirements.txt
python -m pytest tests -q
```

Tests stub external services to verify authentication cookies, access refresh, ownership, validation, prompt construction, PostgreSQL-style relationships and partial failures without incurring API charges. **A real Supabase/PostgreSQL, ImageKit and paid image-generation integration run must be performed after configuring actual credentials.**

### College viva topics

- Why Supabase? Managed PostgreSQL and ready-made secure email/password authentication.
- Why pgAdmin? Explore table rows and run SQL JOINs and indexes visually.
- Why ImageKit? Store files and return CDN URLs; Postgres stores relational metadata.
- Why Pydantic? Validate form JSON to avoid invalid and billable requests.
- Why separate `auth.users`? Supabase manages password hashing and user identity.
- Why no queue? For a small demonstration a synchronous, short function is easier to explain; see HTTP timeout trade-off.

**Sources checked:** [Supabase Python Auth](https://supabase.com/docs/reference/python/auth-signinwithpassword), [Supabase pgAdmin](https://supabase.com/docs/guides/database/pgadmin), [OpenAI Images Edit API](https://developers.openai.com/api/reference/python/resources/images/methods/edit), [ImageKit Upload API](https://imagekit.io/docs/api-reference/upload-file/upload-file).
