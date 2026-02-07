from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.core.database import init_db
from app.api.routes import calendar, stats, nextcloud, alerts, alert_config

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Créer l'application FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclure les routes
app.include_router(calendar.router, prefix=settings.API_V1_STR)
app.include_router(stats.router, prefix=settings.API_V1_STR)
app.include_router(alerts.router, prefix=settings.API_V1_STR)
app.include_router(alert_config.router, prefix=settings.API_V1_STR)
app.include_router(nextcloud.router, prefix=settings.API_V1_STR)


@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage"""
    logger.info("🚀 Démarrage de l'application...")
    
    # Initialiser la base de données
    try:
        init_db()
        logger.info("✅ Base de données initialisée")
    except Exception as e:
        logger.error(f"❌ Erreur initialisation DB: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Nettoyage à l'arrêt"""
    logger.info("👋 Arrêt de l'application...")


@app.get("/")
async def root():
    """Endpoint racine"""
    return {
        "message": "SaaS DrevmBot API",
        "version": "1.0.0",
        "docs": f"{settings.API_V1_STR}/docs"
    }


@app.get("/health")
async def health_check():
    """Health check pour monitoring"""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
