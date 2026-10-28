"""Self-contained tests mock paid services; production has NO demo image mode."""

# Mocking external services makes tests repeatable without leaking paid keys.
from contextlib import contextmanager
from io import BytesIO
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from app import main
from app.database import Base, Creation, GeneratedImage, get_db
from app.media import build_prompt, validate_image
from app.schemas import CreationOptions


@pytest.fixture()
def app_client(monkeypatch, tmp_path):
    # SQLite is used ONLY by this automated test, never as a product fallback.
    engine = create_engine(f'sqlite:///{tmp_path / "test.sqlite"}')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    # Two user IDs simulate accounts from Supabase Auth.
    owner = str(uuid4())
    stranger = str(uuid4())
    state = {'user': owner, 'generation_count': 0, 'uploaded_count': 0}

    # Dependency override stands in for the already-verified Supabase session.
    def get_user():
        return {'id': state['user'], 'email': 'test@example.com'}
    def test_db():
        with Session() as db:
            yield db
    main.app.dependency_overrides[main.current_user] = get_user
    main.app.dependency_overrides[get_db] = test_db

    # No paid image calls: stub only the output, not the application logic.
    def fake_upload(data, folder, ext):
        state['uploaded_count'] += 1
        return f'https://ik.imagekit.io/example/{state["uploaded_count"]}.{ext}', f'file_{state["uploaded_count"]}'
    def fake_generate(reference, prompt, size, quality, fmt):
        state['generation_count'] += 1
        return b'fake-provider-output'
    monkeypatch.setattr(main, 'upload_image', fake_upload)
    monkeypatch.setattr(main, 'generate_image', fake_generate)

    with TestClient(main.app) as client:
        yield client, state, Session, owner, stranger
    main.app.dependency_overrides.clear()


def sample_jpg():
    # Pillow creates a real JPEG for the upload-validation step.
    image = Image.new('RGB', (80, 80), '#8acc99')
    content = BytesIO()
    image.save(content, format='JPEG')
    return content.getvalue()


def payload(**changes):
    values = dict(prompt='How to learn FastAPI', headline='LEARN FASTAPI',
                  subtitle='Beginner to expert', extra_prompt='dark theme',
                  styles=['bold', 'minimal'], image_size='1536x1024',
                  quality='low', output_format='jpeg')
    values.update(changes)
    return values


def create(client, data):
    import json
    return client.post('/api/creations',
        data={'options': json.dumps(data)},
        files={'image': ('reference.jpg', sample_jpg(), 'image/jpeg')})


def test_creation_stored_and_owner_filtered(app_client):
    client, state, Session, owner, stranger = app_client
    # Request creates ONE parent record and TWO image children.
    answer = create(client, payload())
    assert answer.status_code == 200, answer.text
    result = answer.json()
    assert result['headline'] == 'LEARN FASTAPI'
    assert len(result['images']) == 2
    assert all(img['status'] == 'success' for img in result['images'])
    assert state['generation_count'] == 2
    assert state['uploaded_count'] == 3  # reference + 2 results
    # Verify persistence (not only the JSON response).
    with Session() as db:
        assert len(db.scalars(select(Creation)).all()) == 1
        assert len(db.scalars(select(GeneratedImage)).all()) == 2
        assert db.scalars(select(Creation)).first().user_id.hex == owner.replace('-', '')
    # Different user sees no history and cannot open the first user's creation.
    state['user'] = stranger
    assert client.get('/api/creations').json() == []
    assert client.get(f'/api/creations/{result["id"]}').status_code == 404


def test_validation_precedes_expensive_api_calls(app_client):
    client, state, *_ = app_client
    result = create(client, payload(image_size='4000x1000'))
    assert result.status_code == 422
    assert state['generation_count'] == 0
    assert state['uploaded_count'] == 0


def test_styles_custom_text_are_in_provider_prompt():
    # The prompt actually contains user fields and the visual preset.
    options = CreationOptions(**payload(styles=['vibrant']))
    prompt = build_prompt(options, 'vibrant')
    assert 'LEARN FASTAPI' in prompt
    assert 'Beginner to expert' in prompt
    assert 'High-energy design' in prompt


def test_partial_failures_saved(app_client, monkeypatch):
    client, state, Session, *_ = app_client
    # One failed model invocation must not delete the first successful result.
    def sometimes_fails(reference, prompt, size, quality, fmt):
        if 'Elegant minimal layout' in prompt:
            raise RuntimeError('Provider failed')
        return b'generated'
    monkeypatch.setattr(main, 'generate_image', sometimes_fails)
    result = create(client, payload()).json()
    assert [img['status'] for img in result['images']] == ['success', 'failed']
    assert len(client.get('/api/creations').json()[0]['images']) == 2


def test_health_does_not_claim_demo_mode(app_client):
    client, *_ = app_client
    assert client.get('/api/health').json()['mode'] == 'real-api-only'
