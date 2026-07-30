from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configuration de l'application"""
    
    # API
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "SaaS DrevmBot"
    
    # Database
    # Défaut : SQLite local (aucune installation requise) — idéal pour l'app desktop.
    # En production, définir DATABASE_URL (env var) vers Postgres, ex :
    #   postgresql://user:password@localhost:5432/drevmbot
    DATABASE_URL: str = "sqlite:///./drevmbot.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Discord
    DISCORD_WEBHOOK_URL: Optional[str] = None
    
    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # n8n (secret partagé pour authentifier les appels des workflows)
    N8N_WEBHOOK_SECRET: Optional[str] = None

    # Nextcloud (pour export Markdown)
    NEXTCLOUD_URL: Optional[str] = "https://ledream.kflw.io"
    NEXTCLOUD_SHARE_FOLDER: Optional[str] = "/f/33416"
    NEXTCLOUD_USERNAME: Optional[str] = None
    NEXTCLOUD_PASSWORD: Optional[str] = None
    
    # Alertes
    ALERT_CHECK_INTERVAL: int = 3600  # Vérifier toutes les heures
    ALERT_HOURS_AHEAD: int = 2  # Alerter 2h avant événement
    
    # Cache
    CACHE_TTL: int = 3600  # 1 heure

    # n8n automation
    N8N_WEBHOOK_SECRET: Optional[str] = None
    N8N_BASE_URL: Optional[str] = "http://localhost:5678"

    # AI Scoring Agent
    ANTHROPIC_API_KEY: Optional[str] = None
    AI_SCORING_MODEL: str = "claude-sonnet-5"

    # AI Vision Analyst (analyse de captures de charts)
    AI_VISION_MODEL: str = "claude-sonnet-5"

    # Watchlist (CSV Investing.com export)
    WATCHLIST_CSV_PATH: Optional[str] = "data/Portefeuille_Watchlist_03162026.csv"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
