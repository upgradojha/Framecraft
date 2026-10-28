"""Five simple concepts: auth, choose settings, generate, save, read own creations."""
import logging
from uuid import UUID
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from .auth import clear_session, current_user, set_session, supabase
from .config import IMAGE_MODEL, require
from .database import Creation, GeneratedImage, get_db
from .media import build_prompt, generate_image, upload_image, validate_image
from .schemas import CreationOptions, CreationResult, Credentials
from .styles import STYLES

log = logging.getLogger(__name__)
app = FastAPI(title='Framecraft Studio API', version='2.0')

# Allow local React dev server (Vite) to send cookies and call endpoints.
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.exception_handler(RuntimeError)
def handle_runtime_error(request: Request, exc: RuntimeError):
    """Return a clean 500 JSON response when .env variables are missing."""
    return JSONResponse(status_code=500, content={'detail': str(exc)})


@app.get('/api/health')
def health():
    return {'status': 'ok', 'model': IMAGE_MODEL, 'mode': 'real-api-only'}


@app.get('/api/styles')
def styles():
    return [{'id': key, **value} for key, value in STYLES.items()]


@app.post('/api/auth/signup')
def signup(credentials: Credentials, response: Response):
    session = supabase('signup', payload=credentials.model_dump())
    user_data = session.get('user') or (session if 'id' in session else None)
    if session.get('access_token'):
        # Works immediately when Confirm email is OFF in Supabase.
        set_session(response, session)
        return {'user': user_data, 'needs_confirmation': False}
    # If Confirm email stays ON, do not claim the user is logged in.
    return {'user': user_data, 'needs_confirmation': True}


@app.post('/api/auth/login')
def login(credentials: Credentials, response: Response):
    session = supabase('token?grant_type=password', payload=credentials.model_dump())
    set_session(response, session)
    return {'user': session['user']}


@app.get('/api/auth/me')
def me(user=Depends(current_user)):
    return {'user': {'id': user['id'], 'email': user['email']}}


@app.post('/api/auth/logout')
def logout(response: Response):
    clear_session(response)
    return {'ok': True}


def serialize(creation: Creation):
    return CreationResult.model_validate(creation)


@app.get('/api/creations', response_model=list[CreationResult])
def list_creations(user=Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Creation)
        .where(Creation.user_id == UUID(user['id']))
        .options(selectinload(Creation.images))
        .order_by(Creation.created_at.desc())
        .limit(50)
    ).all()
    return [serialize(row) for row in rows]


@app.get('/api/creations/{creation_id}', response_model=CreationResult)
def get_creation(creation_id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    row = db.scalar(
        select(Creation)
        .where(Creation.id == creation_id, Creation.user_id == UUID(user['id']))
        .options(selectinload(Creation.images))
    )
    if not row:
        raise HTTPException(404, 'Creation not found')
    return serialize(row)


@app.post('/api/creations', response_model=CreationResult)
def create_creation(
    options: str = Form(...),
    image: UploadFile = File(...),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    """One request: validate -> upload reference -> call AI -> save results."""
    require('IMAGEKIT_PRIVATE_KEY', 'OPENAI_API_KEY')
    try:
        selected = CreationOptions.model_validate_json(options)
    except ValidationError as error:
        raise HTTPException(422, error.errors(include_context=False)) from error

    original = validate_image(image.file.read(8 * 1024 * 1024 + 1))

    try:
        reference_url, reference_file_id = upload_image(
            original, f'/framecraft/{user["id"]}/references', 'jpg'
        )
    except Exception as error:
        log.exception('Reference image upload failed')
        raise HTTPException(502, 'Reference image upload to ImageKit failed') from error

    row = Creation(
        user_id=UUID(user['id']),
        prompt=selected.prompt,
        headline=selected.headline,
        subtitle=selected.subtitle,
        extra_prompt=selected.extra_prompt,
        image_size=selected.image_size,
        quality=selected.quality,
        output_format=selected.output_format,
        model_name=IMAGE_MODEL,
        reference_url=reference_url,
        reference_file_id=reference_file_id,
    )
    db.add(row)
    db.commit()

    for style in selected.styles:
        result = GeneratedImage(creation_id=row.id, style_name=style, status='failed')
        try:
            final_prompt = build_prompt(selected, style)
            generated = generate_image(
                original,
                final_prompt,
                selected.image_size,
                selected.quality,
                selected.output_format,
            )
            url, imagekit_id = upload_image(
                generated, f'/framecraft/{user["id"]}/{row.id}', selected.output_format
            )
            result.image_url, result.imagekit_file_id = url, imagekit_id
            result.status = 'success'
        except Exception:
            log.exception('Generation failed for style %s', style)
            result.error_message = f'Generation or upload failed for {style}. Check backend logs.'
        db.add(result)
        db.commit()

    return get_creation(row.id, user, db)
