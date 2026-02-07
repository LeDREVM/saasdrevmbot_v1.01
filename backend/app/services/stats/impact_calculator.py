import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class ImpactCalculator:
    """Calcule l'impact réel d'un événement économique sur les prix"""
    
    def calculate_event_impact(
        self,
        price_df: pd.DataFrame,
        event_datetime: datetime
    ) -> Dict:
        """
        Analyse l'impact d'un événement sur les prix
        
        Returns:
        {
            'pre_volatility': float,      # Volatilité 30min avant
            'post_volatility_1h': float,   # Volatilité 1h après
            'post_volatility_4h': float,   # Volatilité 4h après
            'price_change_1h': float,      # Variation % 1h
            'price_change_4h': float,      # Variation % 4h
            'movement_pips': float,        # Mouvement en pips
            'direction': str,              # 'up', 'down', 'neutral'
            'had_impact': bool             # Impact significatif ?
        }
        """
        
        if price_df is None or price_df.empty:
            return None
        
        try:
            # Trouver l'index de l'événement
            event_idx = self._find_closest_index(price_df, event_datetime)
            
            if event_idx is None:
                return None
            
            # Prix de référence à l'événement
            event_price = price_df.loc[event_idx, 'close']
            
            # Volatilité pré-event (30 min avant)
            pre_window = price_df.loc[max(0, event_idx-30):event_idx]
            pre_volatility = self._calculate_volatility(pre_window) if len(pre_window) > 1 else 0
            
            # Volatilité post-event (1h après)
            post_1h_window = price_df.loc[event_idx:min(len(price_df), event_idx+60)]
            post_vol_1h = self._calculate_volatility(post_1h_window) if len(post_1h_window) > 1 else 0
            
            # Volatilité post-event (4h après)
            post_4h_window = price_df.loc[event_idx:min(len(price_df), event_idx+240)]
            post_vol_4h = self._calculate_volatility(post_4h_window) if len(post_4h_window) > 1 else 0
            
            # Variation de prix 1h
            price_1h_later = price_df.loc[min(len(price_df)-1, event_idx+60), 'close']
            change_1h = ((price_1h_later - event_price) / event_price) * 100
            
            # Variation de prix 4h
            price_4h_later = price_df.loc[min(len(price_df)-1, event_idx+240), 'close']
            change_4h = ((price_4h_later - event_price) / event_price) * 100
            
            # Mouvement en pips (estimation: 1 pip = 0.0001 pour forex)
            movement_pips = abs(price_4h_later - event_price) * 10000
            
            # Direction
            direction = 'up' if change_4h > 0.1 else 'down' if change_4h < -0.1 else 'neutral'
            
            # Impact significatif ? (volatilité post > 1.5x pré)
            had_impact = post_vol_1h > (pre_volatility * 1.5) if pre_volatility > 0 else False
            
            return {
                'pre_volatility': round(pre_volatility, 4),
                'post_volatility_1h': round(post_vol_1h, 4),
                'post_volatility_4h': round(post_vol_4h, 4),
                'price_change_1h': round(change_1h, 2),
                'price_change_4h': round(change_4h, 2),
                'movement_pips': round(movement_pips, 1),
                'direction': direction,
                'had_impact': had_impact,
                'event_price': round(event_price, 5)
            }
            
        except Exception as e:
            logger.error(f"Erreur calcul impact: {e}")
            return None
    
    def _find_closest_index(self, df: pd.DataFrame, target_time: datetime) -> Optional[int]:
        """Trouve l'index du prix le plus proche de l'heure de l'événement"""
        
        if 'datetime' not in df.columns and 'date' not in df.columns:
            return None
        
        time_col = 'datetime' if 'datetime' in df.columns else 'date'
        
        # Calculer différence temporelle
        df['time_diff'] = abs(df[time_col] - target_time)
        
        # Trouver l'index minimum
        closest_idx = df['time_diff'].idxmin()
        
        return closest_idx
    
    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """Calcule la volatilité (std des returns)"""
        
        if len(df) < 2:
            return 0.0
        
        # Calcul returns
        returns = df['close'].pct_change().dropna()
        
        if len(returns) == 0:
            return 0.0
        
        # Volatilité = std * sqrt(periods)
        volatility = returns.std() * np.sqrt(len(returns))
        
        return float(volatility)