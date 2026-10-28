"""Test the REAL image API call signature without paying for images."""

# This test replaces the HTTP SDK with a spy, not a product demo generator.
import base64
import sys
from types import SimpleNamespace
from app import media


def test_image_edit_receives_user_size_quality_and_model(monkeypatch):
    # Record what would be sent to the paid image-edit endpoint.
    sent = {}
    class FakeImages:
        def edit(self, **parameters):
            sent.update(parameters)
            return SimpleNamespace(data=[SimpleNamespace(b64_json=base64.b64encode(b'provider-pixels').decode())])
    class FakeOpenAI:
        def __init__(self, **options):
            sent['api_key_used'] = options['api_key']
            self.images = FakeImages()

    # Fake only the external SDK, leaving generate_image() logic intact.
    monkeypatch.setitem(sys.modules, 'openai', SimpleNamespace(OpenAI=FakeOpenAI))
    monkeypatch.setattr(media, 'require', lambda *args: None)
    monkeypatch.setattr(media, 'OPENAI_API_KEY', 'test-api-key')
    monkeypatch.setattr(media, 'IMAGE_MODEL', 'gpt-image-1-mini')
    output = media.generate_image(b'photo', 'Main title: PYTHON', '1024x1024', 'medium', 'webp')
    assert output == b'provider-pixels'
    assert sent['model'] == 'gpt-image-1-mini'
    assert sent['image'] == ('reference.jpg', b'photo', 'image/jpeg')
    assert sent['size'] == '1024x1024'
    assert sent['quality'] == 'medium'
    assert sent['output_format'] == 'webp'
    assert 'PYTHON' in sent['prompt']
