import csv
import os
from datetime import datetime
from typing import List, Dict, Optional
import logging

from app.core.config import settings
from app.services.stats.price_fetcher import PriceFetcher
from app.services.alerts.markdown_exporter import MarkdownExporter

logger = logging.getLogger(__name__)


class WatchlistService:
    """
    Gère la watchlist quotidienne à partir d'un CSV exporté
    (ex: Portefeuille_Watchlist_03162026.csv) et récupère
    les quotes "temps réel" via PriceFetcher / Yahoo Finance.
    """

    def __init__(
        self,
        csv_path: Optional[str] = None,
        markdown_exporter: Optional[MarkdownExporter] = None,
    ):
        self.csv_path = csv_path or settings.WATCHLIST_CSV_PATH
        self.price_fetcher = PriceFetcher()
        self.exporter = markdown_exporter or MarkdownExporter()

    def load_watchlist(self) -> List[Dict]:
        """
        Charge la watchlist depuis le CSV Investing.com exporté.
        On garde surtout le champ "Symbol" et "Name".
        """
        if not self.csv_path or not os.path.exists(self.csv_path):
            logger.warning(f"Watchlist CSV introuvable: {self.csv_path}")
            return []

        rows: List[Dict] = []
        try:
            with open(self.csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Normalise quelques champs utiles
                    rows.append(
                        {
                            "name": row.get("Name") or row.get("Symbol") or "",
                            "symbol": row.get("Symbol") or "",
                            "exchange": row.get("Exchange") or "",
                            "last_raw": row.get("Last") or "",
                            "change_raw": row.get("Chg.") or "",
                            "change_percent_raw": row.get("Chg. %") or "",
                        }
                    )
        except Exception as e:
            logger.error(f"Erreur lecture watchlist CSV {self.csv_path}: {e}")
            return []

        return rows

    def map_symbol_to_backend(self, row_symbol: str) -> str:
        """
        Mappe le symbole provenant du CSV Investing vers les symboles
        utilisés par le backend (PriceFetcher.SYMBOL_MAP).
        """
        symbol = row_symbol.upper()

        mapping = {
            "USD/JPY - US DOLLAR JAPANESE YEN": "USDJPY",
            "USD/JPY - US DOLLAR JAPANESE YEN ": "USDJPY",
            "USD/JPY": "USDJPY",
            "XBR/USD - BRENT SPOT US DOLLAR": "XBRUSD",
            "XBR/USD": "XBRUSD",
            "CRUDE OIL WTI FUTURES": "WTI",
            "CL": "WTI",
            "BTC/USD": "BTCUSD",
            "BTC/USD - BITCOIN": "BTCUSD",
            ".DJI": "DJI",
        }

        return mapping.get(symbol, symbol)

    def fetch_realtime_snapshot(self) -> List[Dict]:
        """
        Récupère les quotes "temps réel" pour tous les éléments de la watchlist
        en utilisant PriceFetcher.get_latest_quote().
        """
        rows = self.load_watchlist()
        if not rows:
            return []

        snapshots: List[Dict] = []
        for row in rows:
            backend_symbol = self.map_symbol_to_backend(row["symbol"])
            quote = self.price_fetcher.get_latest_quote(backend_symbol)
            if not quote:
                logger.warning(f"Aucune quote pour {backend_symbol}")
                continue

            snapshots.append(
                {
                    "name": row["name"],
                    "original_symbol": row["symbol"],
                    "backend_symbol": backend_symbol,
                    "exchange": row["exchange"],
                    "last": quote["last"],
                    "prev_close": quote["prev_close"],
                    "change": quote["change"],
                    "change_percent": quote["change_percent"],
                    "timestamp": quote["timestamp"],
                }
            )

        return snapshots

    def generate_and_export_report(self) -> Optional[str]:
        """
        Génère un rapport Markdown + upload Nextcloud via MarkdownExporter.
        Retourne le chemin local du fichier.
        """
        snapshots = self.fetch_realtime_snapshot()
        if not snapshots:
            logger.info("Aucun snapshot watchlist à exporter")
            return None

        today = datetime.now().strftime("%Y-%m-%d")
        try:
            filepath = self.exporter.export_watchlist_snapshot(
                snapshots=snapshots,
                date=today,
            )
            return filepath
        except Exception as e:
            logger.error(f"Erreur export rapport watchlist: {e}")
            return None

