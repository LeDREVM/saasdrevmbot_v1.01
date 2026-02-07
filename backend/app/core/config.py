from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configuration de l'application"""
    
    # API
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "SaaS DrevmBot"
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/drevmbot"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Discord
    DISCORD_WEBHOOK_URL: Optional[str] = None
    
    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    
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
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
