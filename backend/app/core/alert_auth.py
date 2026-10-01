"""Validate the dashboard's Supabase access token without accepting client identity."""
import os
import hmac
import httpx
from fastapi import Header, HTTPException
from app.core.config import settings


async def require_alert_owner(user_id: str, authorization: str = Header(default="")):
    if not authorization.startswith("Bearer ") or not authorization[7:].strip():
        raise HTTPException(401, "Connexion requise")
    url = os.getenv("SUPABASE_URL", settings.SUPABASE_URL or "").rstrip("/")
    key = os.getenv("SUPABASE_ANON_KEY", settings.SUPABASE_ANON_KEY or "")
    if not url.startswith("https://") or not key:
        raise HTTPException(503, "Authentification des alertes non configurée")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{url}/auth/v1/user", headers={"Authorization": authorization, "apikey": key})
        if response.status_code in (401, 403):
            raise HTTPException(401, "Session expirée")
        response.raise_for_status()
        identity = response.json().get("id")
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, "Vérification de session indisponible")
    if not identity:
        raise HTTPException(401, "Session invalide")
    if identity != user_id:
        raise HTTPException(403, "Accès interdit")
    return identity


def require_notification_admin(x_n8n_secret: str = Header(default="")):
    expected = os.getenv('N8N_WEBHOOK_SECRET', settings.N8N_WEBHOOK_SECRET or '')
    if not expected:
        raise HTTPException(503, 'Envoi global non configuré')
    if not hmac.compare_digest(x_n8n_secret, expected):
        raise HTTPException(403, 'Accès interdit')
