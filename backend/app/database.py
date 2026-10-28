"""Two simple SQLAlchemy tables. SQL setup also lives in sql/01_schema.sql."""
from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from .config import DATABASE_URL, require


def new_id() -> str:
    # Generate a unique ID for each creation and image.
    return str(uuid4())


def timestamp() -> datetime:
    # Store dates consistently in UTC.
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    # SQLAlchemy uses this base to discover our table definitions.
    pass


class Creation(Base):
    # One row represents one request by one registered user.
    __tablename__ = 'creations'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    headline: Mapped[str] = mapped_column(String(140), default='')
    subtitle: Mapped[str] = mapped_column(String(200), default='')
    extra_prompt: Mapped[str] = mapped_column(Text, default='')
    image_size: Mapped[str] = mapped_column(String(20))
    quality: Mapped[str] = mapped_column(String(12))
    output_format: Mapped[str] = mapped_column(String(8))
    model_name: Mapped[str] = mapped_column(String(100))
    reference_url: Mapped[str] = mapped_column(Text)
    reference_file_id: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=timestamp)

    # A creation can have up to three image rows, one for each style.
    images: Mapped[list['GeneratedImage']] = relationship(
        back_populates='creation',
        cascade='all, delete-orphan',
        order_by='GeneratedImage.created_at',
    )


class GeneratedImage(Base):
    # Each row stores the result of one OpenAI image-edit call.
    __tablename__ = 'generated_images'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    creation_id: Mapped[str] = mapped_column(
        ForeignKey('creations.id', ondelete='CASCADE'), index=True
    )
    style_name: Mapped[str] = mapped_column(String(30))
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    imagekit_file_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(12))
    error_message: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=timestamp)

    creation: Mapped[Creation] = relationship(back_populates='images')


# The engine is lazy, so the app can show a helpful setup error before connecting.
engine = None
SessionLocal = None


def get_db():
    """Open one session per HTTP request; close it when the request ends."""
    global engine, SessionLocal
    require('DATABASE_URL')
    if SessionLocal is None:
        # Normalize URL to use psycopg (v3) driver automatically.
        db_url = DATABASE_URL
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql+psycopg://', 1)
        elif db_url.startswith('postgresql://') and '+psycopg' not in db_url:
            db_url = db_url.replace('postgresql://', 'postgresql+psycopg://', 1)

        engine = create_engine(db_url, pool_pre_ping=True)
        SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    with SessionLocal() as session:
        yield session
