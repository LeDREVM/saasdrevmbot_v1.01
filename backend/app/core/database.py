from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from typing import Generator
from app.core.config import settings

# Base pour les modèles
Base = declarative_base()

# Créer l'engine SQLAlchemy
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
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
