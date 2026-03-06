from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional
import logging

from app.services.alerts.nextcloud_uploader import NextcloudUploader
from app.services.alerts.markdown_exporter import MarkdownExporter
from app.core.config import settings

router = APIRouter(prefix="/nextcloud", tags=["Nextcloud"])

logger = logging.getLogger(__name__)

# Initialiser les services
uploader = NextcloudUploader()
exporter = MarkdownExporter(auto_upload=True)


@router.get("/status")
async def get_nextcloud_status():
    """
    📊 Vérifie le statut de connexion Nextcloud
    
    Returns:
    ```json
    {
        "connected": true,
        "nextcloud_url": "https://ledream.kflw.io",
        "configured": true,
        "last_sync": "2026-02-06T10:30:00"
    }
    ```
    """
    
    # Vérifier si Nextcloud est configuré
    configured = bool(
        settings.NEXTCLOUD_URL and 
        settings.NEXTCLOUD_USERNAME and 
        settings.NEXTCLOUD_PASSWORD
    )
    
    if not configured:
        return JSONResponse(content={
            "connected": False,
            "nextcloud_url": settings.NEXTCLOUD_URL or "Non configuré",
            "configured": False,
            "message": "Nextcloud non configuré. Vérifier les variables d'environnement."
        })
    
    # Tester la connexion
    try:
        # Créer le dossier de test (retourne True si existe déjà)
        test_connection = uploader.create_folder("ForexBot")
        
        return JSONResponse(content={
            "connected": test_connection,
            "nextcloud_url": settings.NEXTCLOUD_URL,
            "configured": True,
            "username": settings.NEXTCLOUD_USERNAME,
            "share_folder": settings.NEXTCLOUD_SHARE_FOLDER,
            "message": "✅ Connexion réussie" if test_connection else "❌ Connexion échouée"
        })
    except Exception as e:
        logger.error(f"Erreur test connexion Nextcloud: {e}")
        return JSONResponse(content={
            "connected": False,
            "nextcloud_url": settings.NEXTCLOUD_URL,
            "configured": True,
            "error": str(e),
            "message": "❌ Erreur de connexion"
        })


@router.post("/sync/all")
async def sync_all_reports(background_tasks: BackgroundTasks):
    """
    🔄 Synchronise tous les rapports vers Nextcloud
    
    Lance la synchronisation en arrière-plan de tous les rapports
    disponibles dans le dossier local.
    """
    
    if not settings.NEXTCLOUD_URL:
        raise HTTPException(
            status_code=400,
            detail="Nextcloud non configuré"
        )
    
    # Lancer la sync en background
    background_tasks.add_task(sync_all_reports_task)
    
    return JSONResponse(content={
        "status": "started",
        "message": "Synchronisation lancée en arrière-plan"
    })


async def sync_all_reports_task():
    """Tâche de synchronisation en arrière-plan"""
    import os
    from pathlib import Path
    
    reports_dir = Path(exporter.output_dir)
    
    if not reports_dir.exists():
        logger.warning(f"Dossier rapports inexistant: {reports_dir}")
        return
    
    synced_count = 0
    failed_count = 0
    
    # Uploader tous les fichiers .md
    for md_file in reports_dir.glob("*.md"):
        try:
            success = uploader.upload_file(str(md_file))
            if success:
                synced_count += 1
                logger.info(f"✅ Synced: {md_file.name}")
            else:
                failed_count += 1
                logger.warning(f"❌ Failed: {md_file.name}")
        except Exception as e:
            failed_count += 1
            logger.error(f"Erreur sync {md_file.name}: {e}")
    
    logger.info(f"Sync terminée: {synced_count} réussis, {failed_count} échoués")


@router.post("/sync/report/{filename}")
async def sync_single_report(filename: str):
    """
    📤 Synchronise un rapport spécifique
    
    Args:
        filename: Nom du fichier à synchroniser (ex: predictions_EURUSD_2026-02-06.md)
    """
    
    if not settings.NEXTCLOUD_URL:
        raise HTTPException(
            status_code=400,
            detail="Nextcloud non configuré"
        )
    
    from pathlib import Path
    
    reports_dir = Path(exporter.output_dir)
    file_path = reports_dir / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Fichier non trouvé: {filename}"
        )
    
    try:
        success = uploader.upload_file(str(file_path))
        
        if success:
            return JSONResponse(content={
                "status": "success",
                "filename": filename,
                "message": f"✅ {filename} synchronisé"
            })
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Échec de l'upload: {filename}"
            )
    except Exception as e:
        logger.error(f"Erreur sync {filename}: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/reports/list")
async def list_local_reports():
    """
    📋 Liste tous les rapports locaux disponibles
    
    Returns:
    ```json
    {
        "reports": [
            {
                "filename": "predictions_EURUSD_2026-02-06.md",
                "size": 12345,
                "created": "2026-02-06T10:30:00",
                "type": "predictions"
            }
        ],
        "count": 10
    }
    ```
    """
    
    from pathlib import Path
    import os
    from datetime import datetime
    
    reports_dir = Path(exporter.output_dir)
    
    if not reports_dir.exists():
        return JSONResponse(content={
            "reports": [],
            "count": 0,
            "message": "Aucun rapport disponible"
        })
    
    reports = []
    
    for md_file in sorted(reports_dir.glob("*.md"), key=os.path.getmtime, reverse=True):
        stat = md_file.stat()
        
        # Déterminer le type de rapport
        report_type = "unknown"
        if "predictions" in md_file.name:
            report_type = "predictions"
        elif "stats_report" in md_file.name:
            report_type = "stats"
        elif "weekly_summary" in md_file.name:
            report_type = "weekly"
        
        reports.append({
            "filename": md_file.name,
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "type": report_type
        })
    
    return JSONResponse(content={
        "reports": reports,
        "count": len(reports),
        "directory": str(reports_dir)
    })


@router.post("/generate-and-sync/predictions")
async def generate_and_sync_predictions(
    symbol: str,
    background_tasks: BackgroundTasks
):
    """
    🎯 Génère un rapport de prédictions et le synchronise
    
    Args:
        symbol: Symbole à analyser (EURUSD, GBPUSD, etc.)
    """
    
    if not settings.NEXTCLOUD_URL:
        raise HTTPException(
            status_code=400,
            detail="Nextcloud non configuré"
        )
    
    # Lancer la génération en background
    background_tasks.add_task(
        generate_predictions_task,
        symbol
    )
    
    return JSONResponse(content={
        "status": "started",
        "symbol": symbol,
        "message": f"Génération du rapport de prédictions pour {symbol} lancée"
    })


async def generate_predictions_task(symbol: str):
    """Génère et sync un rapport de prédictions"""
    from app.services.alerts.alert_predictor import AlertPredictor
    from app.services.economic_calendar.calendar_aggregator import CalendarAggregator
    from app.core.database import get_db
    
    try:
        # Récupérer les événements à venir
        aggregator = CalendarAggregator()
        upcoming_events = aggregator.get_today_events()
        
        # Générer les prédictions
        predictor = AlertPredictor()
        db = next(get_db())
        
        predictions = []
        for event in upcoming_events:
            prediction = predictor.predict_upcoming_impact(event, symbol, db)
            if prediction:
                predictions.append(prediction)
        
        # Générer le rapport (auto-upload activé)
        if predictions:
            filepath = exporter.export_daily_predictions(predictions, symbol)
            logger.info(f"✅ Rapport généré et synchronisé: {filepath}")
        else:
            logger.warning(f"Aucune prédiction disponible pour {symbol}")
            
    except Exception as e:
        logger.error(f"Erreur génération rapport {symbol}: {e}")


@router.post("/test-connection")
async def test_nextcloud_connection():
    """
    🧪 Teste la connexion Nextcloud
    
    Crée un fichier de test et tente de l'uploader.
    """
    
    if not settings.NEXTCLOUD_URL:
        raise HTTPException(
            status_code=400,
            detail="Nextcloud non configuré"
        )
    
    import tempfile
    from datetime import datetime
    
    try:
        # Créer un fichier de test
        test_content = f"""# Test Connexion Nextcloud

Fichier de test généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}

✅ Si vous voyez ce fichier, la connexion fonctionne !

---

**Configuration:**
- URL: {settings.NEXTCLOUD_URL}
- Username: {settings.NEXTCLOUD_USERNAME}
- Dossier: ForexBot/reports/
"""
        
        # Créer un fichier temporaire
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(test_content)
            temp_path = f.name
        
        # Uploader
        filename = f"test_connection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        success = uploader.upload_file(temp_path, filename)
        
        # Nettoyer
        import os
        os.unlink(temp_path)
        
        if success:
            return JSONResponse(content={
                "status": "success",
                "message": "✅ Connexion réussie !",
                "filename": filename,
                "url": f"{settings.NEXTCLOUD_URL}/ForexBot/reports/{filename}"
            })
        else:
            raise HTTPException(
                status_code=500,
                detail="Upload échoué"
            )
            
    except Exception as e:
        logger.error(f"Erreur test connexion: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.delete("/reports/{filename}")
async def delete_local_report(filename: str):
    """
    🗑️ Supprime un rapport local
    
    Note: Ne supprime PAS le fichier sur Nextcloud
    """
    
    from pathlib import Path
    import os
    
    reports_dir = Path(exporter.output_dir)
    file_path = reports_dir / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Fichier non trouvé: {filename}"
        )
    
    try:
        os.unlink(file_path)
        return JSONResponse(content={
            "status": "success",
            "message": f"✅ {filename} supprimé"
        })
    except Exception as e:
        logger.error(f"Erreur suppression {filename}: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
