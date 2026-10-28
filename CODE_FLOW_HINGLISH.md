# Framecraft code flow — Hinglish explanation for viva

**Purpose:** Kisi student ko project ka flow asaani se samajh aaye. Har Python file mein important lines ke saath `#` comments hain; JS logic ke saath `//` comments hain. Yahaan line-by-line responsibilities aur data flow explain kiya gaya hai.

## 1. Browser home route `/`

`frontend/src/App.jsx` mein `App()` component hai.

1. `const [user, setUser] = useState(null)` — current user ka data rakhta hai.
2. `const [checking, setChecking] = useState(true)` — cookie check ke time loader rakhta hai.
3. `useEffect(..., [])` — page open hote hi ek baar chalta hai.
4. `api.me()` — backend `GET /api/auth/me` par request bhejta hai.
5. Server cookie validate kare toh `setUser(...)`; warna `setUser(null)`.
6. `user ? <Dashboard .../> : <AuthPage .../>` — decision browser ko nahi, validated backend result ko follow karta hai.

**Question: Cookie kyun?** Login ke baad server `HttpOnly` cookie set karta hai; JavaScript token nahi dekh sakta. Reload pe browser cookie automatically send karta hai.

## 2. User registration

`AuthPage()` mein email+password fields hain. Register tab select karne par `api.signup()` call hota hai:

```text
Browser -> POST /api/auth/signup -> auth.py -> Supabase Auth /signup
                                          |
                              Supabase auth.users row
                                          |
                                access & refresh token
                                          |
                           HttpOnly cookies in response
                                          |
                                Dashboard rendered
```

`backend/app/main.py` mein `signup()` user ka password database mein khud save **nahi** karta; Supabase Auth securely handle karta hai. Agar Supabase mein Confirm email ON rahega, session turant nahi milega aur UI verification message dikhayega.

## 3. Login and cookie refresh

`login()` credentials ko Supabase `/auth/v1/token?grant_type=password` par bhejta hai. Success par `set_session()` access aur refresh cookies set karta hai. Har protected API route mein `Depends(current_user)` rehta hai. `current_user()`:

1. Browser ke cookies read karta hai.
2. Access token hai toh Supabase `/auth/v1/user` se usko **verify** karta hai.
3. Access expired ho toh refresh token se new access token le sakta hai.
4. Refresh ke baad browser ko new cookies send karta hai.
5. Dono invalid hue toh **401**; user ko login page milega.

## 4. Creation form and AI settings

`Dashboard()` mein `form` object contains:

| Field | User enters | Provider impact |
|---|---|---|
| `prompt` | Main topic / video idea | AI prompt main subject |
| `headline` | Exact big text | AI typography instruction |
| `subtitle` | Smaller supporting text | AI typography instruction |
| `extra_prompt` | Own visual direction | More detail in AI prompt |
| `styles` | Bold, Minimal, Vibrant | Separate image per selected style |
| `image_size` | Landscape, Square, Portrait | `images.edit(size=...)` |
| `quality` | Low, Medium, High | `images.edit(quality=...)` |
| `output_format` | JPEG, WebP, PNG | `images.edit(output_format=...)` |

- `toggleStyle()` manages selected style IDs. Minimum one, maximum three.
- `update()` changes exactly one field in React state.
- `generate()` builds a `FormData` with photo (`image`) and stringified settings (`options`).
- `api.create()` makes **one** `POST /api/creations` request.

## 5. Server's generation function (`backend/app/main.py`)

Read the `create_creation()` function from top to bottom:

1. `CreationOptions.model_validate_json(options)` — Pydantic stops invalid quality/size/styles **before** spending AI credits.
2. `validate_image(image.file.read(...))` — loads JPEG/PNG/WebP and resizes to reasonable dimensions.
3. `upload_image(...)` — reference photo to ImageKit; returns `(url, fileId)`.
4. `Creation(...)` — parent record containing **verified** `user['id']`, prompt, output settings and reference URL.
5. `db.add(row); db.commit()` — save the creation in Supabase PostgreSQL.
6. `for style in selected.styles:` — simple for-loop. **No queue/job table.**
7. `build_prompt(...)` — style preset + headline + subtitle + directions all become an AI prompt.
8. `generate_image(...)` — `OpenAI.images.edit`, with the uploaded photo and all selected settings.
9. `upload_image(...)` — AI bytes to ImageKit; returns real CDN URL / file ID.
10. `GeneratedImage(...)` — child record saves success status, URL and ImageKit ID.
11. On provider error, image row with `failed` status is saved, other selected styles continue.
12. `return get_creation(...)` — Pydantic response contains parent settings and child image rows.

**Question: Image kahaan save hai?** Real binary file ImageKit mein. Postgres mein `image_url`, `imagekit_file_id` aur creation metadata. This keeps relational data simple.

## 6. PostgreSQL models (`backend/app/database.py`)

`Base` = SQLAlchemy model superclass.

`Creation` fields: `id` primary key; `user_id` foreign key to Supabase `auth.users` (created via SQL file), `prompt`, `headline`, `subtitle`, `extra_prompt`, `image_size`, `quality`, `output_format`, `model_name`, `reference_url`, `reference_file_id`, `created_at`.

`GeneratedImage` fields: `id` primary key; `creation_id` foreign key; `style_name`, `image_url`, `imagekit_file_id`, `status`, `error_message`, `created_at`.

`relationship()` is the **Python-side relationship**. SQL `FOREIGN KEY` is the **database-side relationship**. One `Creation` has many `GeneratedImage`s.

`get_db()` opens and automatically closes one SQLAlchemy session per API request. The database URL must be a Supabase PostgreSQL URL; product code never silently switches to SQLite.

## 7. My creations — security explanation

`GET /api/creations` uses:

```python
# The UUID comes from verified Supabase auth, not the browser's query parameters.
select(Creation).where(Creation.user_id == UUID(user['id']))
```

- User A signs in: history shows A's creations.
- User B signs in: history shows B's creations.
- User B guesses A's creation ID: `GET /api/creations/{id}` returns **404** because ownership is checked.
- Every `images` child belongs to a parent creation. No `jobs` table exists.

## 8. pgAdmin — SQL viva

Use `sql/01_schema.sql` in Supabase SQL Editor for tables and indexes. Connect pgAdmin to Supabase with the Session Pooler host, login and SSL settings from the Dashboard. The SQL JOIN examples in `sql/02_learning_queries.sql` show how to retrieve images with creation prompts and users.

## 9. How to change the AI model

In `backend/.env` update:

```dotenv
IMAGE_MODEL=gpt-image-1-mini
```

`media.py` contains one `generate_image()` function. For another **OpenAI image-edit compatible** model, changing `IMAGE_MODEL` may be enough. Other vendors have different endpoints and need this function adapted. Note: **GPT-2 is a text model, not an image-generation model**. It cannot replace an image model as-is.

## 10. Why tests have fake API responses

`backend/tests/` uses monkeypatched API functions. This is **testing only**, not application demo mode. Running the application with missing API keys does **not** generate fake thumbnails. Tests verify business logic without paid network requests; use real credentials to perform an end-to-end image test.
