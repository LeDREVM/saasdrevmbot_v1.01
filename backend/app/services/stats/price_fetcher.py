import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class PriceFetcher:
    """Récupère les données de prix pour analyse de corrélation"""
    
    # Mapping symboles trading → Yahoo Finance
    SYMBOL_MAP = {
        # Forex (via ETF)
        'EURUSD': 'EURUSD=X',
        'GBPUSD': 'GBPUSD=X',
        'USDJPY': 'JPY=X',
        'AUDUSD': 'AUDUSD=X',
        'USDCAD': 'CAD=X',
        'USDCHF': 'CHF=X',
        
        # Indices
        'SPX': '^GSPC',
        'NDX': '^NDX',
        'DJI': '^DJI',
        'DAX': '^GDAXI',
        
        # Commodities
        'XAUUSD': 'GC=F',  # Gold futures
        'XBRUSD': 'CL=F',  # Crude oil
    }
    
    def __init__(self):
        self.cache = {}  # Simple cache mémoire
    
    def get_price_around_event(
        self, 
        symbol: str, 
        event_datetime: datetime,
        minutes_before: int = 30,
        minutes_after: int = 240
    ) -> Optional[pd.DataFrame]:
        """
        Récupère les prix autour d'un événement économique
        
        Returns DataFrame avec colonnes: timestamp, open, high, low, close, volume
        """
        
        yahoo_symbol = self.SYMBOL_MAP.get(symbol, symbol)
        
        # Fenêtre de temps
        start_time = event_datetime - timedelta(minutes=minutes_before)
        end_time = event_datetime + timedelta(minutes=minutes_after)
        
        cache_key = f"{yahoo_symbol}_{start_time.isoformat()}_{end_time.isoformat()}"
        
        # Check cache
        if cache_key in self.cache:
            logger.debug(f"Cache hit: {cache_key}")
            return self.cache[cache_key]
        
        try:
            # Télécharger données intraday (1 min)
            ticker = yf.Ticker(yahoo_symbol)
            df = ticker.history(
                start=start_time,
                end=end_time,
                interval='1m'
            )
            
            if df.empty:
                logger.warning(f"Pas de données pour {symbol} à {event_datetime}")
                return None
            
            # Reset index pour avoir timestamp comme colonne
            df = df.reset_index()
            df.columns = [c.lower() for c in df.columns]
            
            # Cache
            self.cache[cache_key] = df
            
            logger.info(f"✅ Prix récupérés: {symbol} ({len(df)} bougies)")
            return df
            
        except Exception as e:
            logger.error(f"Erreur fetch prix {symbol}: {e}")
            return None
    
    def get_daily_prices(
        self,
        symbol: str,
        days_back: int = 30
    ) -> Optional[pd.DataFrame]:
        """Récupère les prix daily pour analyse long terme"""
        
        yahoo_symbol = self.SYMBOL_MAP.get(symbol, symbol)
        
        try:
            ticker = yf.Ticker(yahoo_symbol)
            df = ticker.history(period=f"{days_back}d", interval='1d')
            
            if df.empty:
                return None
            
            df = df.reset_index()
            df.columns = [c.lower() for c in df.columns]
            
            return df
            
        except Exception as e:
            logger.error(f"Erreur fetch daily {symbol}: {e}")
            return None