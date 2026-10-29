"""Image validation, ImageKit uploads, and the real AI image-edit call."""
import base64
import io
from uuid import uuid4
import httpx
from PIL import Image, ImageOps, UnidentifiedImageError
from fastapi import HTTPException
from .config import IMAGEKIT_PRIVATE_KEY, OPENAI_API_KEY, IMAGE_MODEL, MAX_UPLOAD_MB, require
from .styles import STYLES


def validate_image(data: bytes) -> bytes:
    """Reject invalid files and produce a small JPEG for image editing."""
    if not data or len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f'Image must be smaller than {MAX_UPLOAD_MB} MB')
    try:
        # Pillow actually parses the image; filenames alone cannot prove type.
        with Image.open(io.BytesIO(data)) as image:
            if image.format not in ('JPEG', 'PNG', 'WEBP') or image.width * image.height > 25_000_000:
                raise ValueError('Only JPEG/PNG/WebP under 25 megapixels are allowed')
            # Fix phone-photo rotation and cap size before passing it to OpenAI.
            image = ImageOps.exif_transpose(image).convert('RGB')
            image.thumbnail((2048, 2048))
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=88)
            return output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as error:
        raise HTTPException(400, f'Invalid image: {error}') from error


def upload_image(data: bytes, folder: str, extension: str) -> tuple[str, str]:
    """Upload bytes to ImageKit; return (public CDN URL, ImageKit file ID)."""
    require('IMAGEKIT_PRIVATE_KEY')
    name = f'{uuid4()}.{extension}'
    with httpx.Client(timeout=90) as client:
        result = client.post(
            'https://upload.imagekit.io/api/v1/files/upload',
            auth=(IMAGEKIT_PRIVATE_KEY, ''),
            data={'fileName': name, 'folder': folder, 'useUniqueFileName': 'true'},
            files={'file': (name, data, f'image/{extension}')},
        )
    result.raise_for_status()
    body = result.json()
    return body['url'], body['fileId']


def build_prompt(options, style: str) -> str:
    """Combine the user's fields with the selected style's instructions."""
    return '\n'.join([
        'Create a professionally designed social media thumbnail using the uploaded reference photo.',
        'Keep the main person recognizable and appropriate.',
        f"Visual style: {STYLES[style]['instruction']}",
        f'Subject: {options.prompt}',
        f'EXACT MAIN TEXT: {options.headline or "No headline required"}',
        f'EXACT SUPPORTING TEXT: {options.subtitle or "No supporting text required"}',
        f'Additional directions: {options.extra_prompt or "None"}',
        'Use clear text hierarchy and legible typography. Do not add unrequested words.',
    ])


def generate_image(reference: bytes, prompt: str, size: str, quality: str, fmt: str) -> bytes:
    """Real image editing. No offline/demo fallback: missing keys cause an error."""
    require('OPENAI_API_KEY')
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY, timeout=180, max_retries=0)
    result = client.images.edit(
        model=IMAGE_MODEL,
        image=('reference.jpg', reference, 'image/jpeg'),
        prompt=prompt,
        size=size,
        quality='high',
        output_format='jpeg',
    )
    if not result.data or not result.data[0].b64_json:
        raise RuntimeError('Image API returned no image')
    return base64.b64decode(result.data[0].b64_json)
