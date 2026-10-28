# Framecraft Studio — Simple Setup (Hinglish)

**Stack:** React + FastAPI + Supabase Auth + Supabase PostgreSQL + pgAdmin + ImageKit + real OpenAI image-edit API.

**Demo mode / job queues / SSE / local production SQLite:** sab hata diya hai. Real API key zaroori hai; fake images nahi banti.

## Step 1 — Install tools

- Python **3.11+**
- Node.js **20+**
- pgAdmin 4 (optional; Supabase SQL Editor bhi chalega)
- Supabase, ImageKit aur OpenAI API accounts

## Step 2 — Supabase

1. Supabase Dashboard → **New project**.
2. **Authentication → Providers → Email** → Enable Email; for the simple college flow, **Confirm email OFF** (disable email verification) as requested. With confirmation ON, students must verify email before a session starts.
3. **SQL Editor → New query** → paste and run **`sql/01_schema.sql`** once.
4. **Connect** button → **Session pooler → View parameters** → copy the connection string. It is your `DATABASE_URL`.
5. **Settings / Data API / API Keys** → copy the `SUPABASE_URL` and anon/publishable key. **NEVER use the `service_role` key in React.**

## Step 3 — ImageKit / OpenAI

1. ImageKit Dashboard → Developer options → private API key. Images live in ImageKit, PostgreSQL stores their URLs and file IDs.
2. OpenAI API key with billing enabled. The default image model is `gpt-image-1-mini` (low-cost, actual image editing). **No demo fallback.**
3. To switch image models later, edit only `IMAGE_MODEL` in `.env`, then restart FastAPI. The new model MUST support **image editing** and selected sizes/quality. GPT-2 is a text model, **not** an image generation model.

## Step 4 — Configure secrets

Copy **`backend/.env.example` → `backend/.env`**, then fill all real values:

```dotenv
DATABASE_URL=postgresql+psycopg://postgres.PROJECT_ID:YOUR_PASSWORD@YOUR_POOLER_HOST:5432/postgres?sslmode=require
SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
SUPABASE_ANON_KEY=YOUR_ANON_OR_PUBLISHABLE_KEY
IMAGEKIT_PRIVATE_KEY=YOUR_IMAGEKIT_PRIVATE_KEY
IMAGEKIT_URL_ENDPOINT=https://ik.imagekit.io/YOUR_ENDPOINT
OPENAI_API_KEY=YOUR_OPENAI_KEY
IMAGE_MODEL=gpt-image-1-mini
COOKIE_SECURE=false
```

`DATABASE_URL` me agar password me `@`, `#`, `:` etc hai to URL-encode karna padega. Supabase ke **Connect** dialog se exact host aur username lena. Real keys kabhi GitHub me upload mat karna.

## Step 5 — Run

**Windows:** project folder me `start_windows.bat` double-click (pehli baar packages install honge). It starts FastAPI and React in separate terminals.

**Manual / macOS / Linux:**

Terminal 1:
```bash
cd backend
python -m venv .venv
# macOS / Linux: source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Terminal 2:
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. `http://localhost:8000/docs` par FastAPI swagger docs milenge.

## Step 6 — Use

1. Register → email/password → Supabase `auth.users` me user record.
2. Auto session cookie → dashboard opens. Refresh karein to `GET /api/auth/me` cookie verify karta hai.
3. Photo upload, one-to-three styles, main headline, supporting line, extra directions, size, quality, format choose karein.
4. Click Generate → FastAPI uploads reference → calls real AI model for each style → uploads results to ImageKit → saves records in PostgreSQL.
5. My creations tab → **sirf is user** ke saved images.
6. Sign out → cookies clear, back to login.

## pgAdmin connection

**Register → Server → Connection**:
- Host: Supabase session pooler host
- Port: value from Connect (often `5432`)
- Maintenance database: `postgres`
- Username: pooler username from Connect (often `postgres.PROJECT_ID`)
- Password: Supabase database password
- SSL: configure Root Certificate from Supabase Database Settings per their pgAdmin guide

Then open `public.creations` and `public.generated_images`. More learning SQL is in **`sql/02_learning_queries.sql`**. Do not run the UUID example unchanged; replace the sample ID first.

## Common issues

- Signup asks for verification → disable Confirm email in Supabase or verify email first.
- `Database connect failed` → check pooler URL, SSL, password encoding, Supabase project state and that `sql/01_schema.sql` ran.
- `401 Session expired` → sign in again; API securely refreshes sessions when possible.
- `ImageKit upload failed` → check private key and ImageKit account permissions.
- AI result status `failed` → check backend terminal for provider error, credit balance, model availability or unsupported options. Successful styles are still saved.
- No frontend page → start Vite with `npm run dev` and open port 5173.

**Code explanation:** `CODE_FLOW_HINGLISH.md`; full instructions: `README.md`.
