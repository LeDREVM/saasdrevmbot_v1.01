from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from typing import Generator
from app.core.config import settings

# Base pour les modèles
Base = declarative_base()

# Créer l'engine SQLAlchemy.
# SQLite (app desktop locale) et Postgres (prod) n'acceptent pas les mêmes
# options de pool : on adapte selon le driver de DATABASE_URL.
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        # Autorise l'accès depuis les threads FastAPI/uvicorn
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency pour obtenir une session de base de données
    
    Usage dans FastAPI:
    ```python
    @app.get("/endpoint")
    def endpoint(db: Session = Depends(get_db)):
        ...
    ```
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialise la base de données (crée les tables)"""
    # Importer tous les modèles pour qu'ils soient enregistrés
    from app.models import database, alert_settings
    Base.metadata.create_all(bind=engine)
