"""Single place for all settings. Copy backend/.env.example to backend/.env."""
import os
from pathlib import Path
from dotenv import load_dotenv

env_file = Path(__file__).resolve().parents[1] / '.env'
if env_file.exists():
    load_dotenv(env_file, override=True)

DATABASE_URL = os.getenv('DATABASE_URL', '').strip().strip('"').strip("'")
SUPABASE_URL = os.getenv('SUPABASE_URL', '').strip().rstrip('/')
SUPABASE_PUBLISHABLE_KEY = os.getenv('SUPABASE_PUBLISHABLE_KEY', '').strip()
IMAGEKIT_PRIVATE_KEY = os.getenv('IMAGEKIT_PRIVATE_KEY', '').strip()
IMAGEKIT_URL_ENDPOINT = os.getenv('IMAGEKIT_URL_ENDPOINT', '').strip().rstrip('/')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '').strip().strip('"').strip("'")
IMAGE_MODEL = os.getenv('IMAGE_MODEL', 'gpt-image-1-mini').strip()
COOKIE_SECURE = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
MAX_UPLOAD_MB = 8


def require(*names: str) -> None:
    """Raise a readable error if any required setting is missing."""
    missing = [name for name in names if not globals().get(name)]
    if missing:
        raise RuntimeError('Missing backend/.env settings: ' + ', '.join(missing))
