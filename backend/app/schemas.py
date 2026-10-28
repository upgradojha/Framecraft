"""Pydantic checks user-supplied generation settings BEFORE making paid API calls."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class Credentials(BaseModel):
    # Supabase handles password hashing; we just validate request format.
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=6, max_length=128)


class CreationOptions(BaseModel):
    # Every dropdown in React maps to one field here.
    prompt: str = Field(min_length=5, max_length=1500)
    headline: str = Field(default='', max_length=140)
    subtitle: str = Field(default='', max_length=200)
    extra_prompt: str = Field(default='', max_length=1000)
    styles: list[Literal['bold', 'minimal', 'vibrant']] = Field(min_length=1, max_length=3)
    image_size: Literal['1536x1024', '1024x1024', '1024x1536'] = '1536x1024'
    quality: Literal['low', 'medium', 'high'] = 'low'
    output_format: Literal['png', 'jpeg', 'webp'] = 'jpeg'

    @field_validator('styles')
    @classmethod
    def distinct_styles(cls, value):
        # Prevent duplicate API calls for the same style.
        if len(value) != len(set(value)):
            raise ValueError('Choose distinct styles')
        return value

    @field_validator('prompt', mode='before')
    @classmethod
    def trim_prompt(cls, value):
        # Remove accidental spaces BEFORE checking min_length=5.
        if isinstance(value, str):
            return value.strip()
        return value


class ImageResult(BaseModel):
    # from_attributes reads model fields from SQLAlchemy objects.
    model_config = {'from_attributes': True}

    id: str
    style_name: str
    image_url: str | None
    status: str
    error_message: str | None


class CreationResult(BaseModel):
    # Responses are intentionally explicit, so frontend receives predictable JSON.
    model_config = {'from_attributes': True}

    id: str
    prompt: str
    headline: str
    subtitle: str
    extra_prompt: str
    image_size: str
    quality: str
    output_format: str
    model_name: str
    reference_url: str
    created_at: datetime
    images: list[ImageResult]
