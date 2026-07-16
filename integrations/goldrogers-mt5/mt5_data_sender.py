import MetaTrader5 as mt5
import pandas as pd
import time
import requests
import json
from datetime import datetime
import os
import sys

# Configuration
# On envoie les 3 timeframes dont le moteur a besoin (build_context : H4/M15/M5)
# pour que le dashboard cloud/Linux tourne 100 % sur les vraies bougies MT5.
CONFIG = {
    'symbols': ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'US30', 'XBRUSD'],
    'timeframes': [
        (mt5.TIMEFRAME_H4, 'H4', 150),
        (mt5.TIMEFRAME_M15, 'M15', 200),
        (mt5.TIMEFRAME_M5, 'M5', 250),
    ],
    'send_interval': 300,  # 5 minutes
    'api_url': os.environ.get('MARKET_DATA_API_URL', ''),  # ex: http://localhost:8800/api/market-data
}

def initialize_mt5():
    # Désinitialiser MT5 si déjà initialisé
    mt5.shutdown()
    
    # Initialiser MT5
    if not mt5.initialize(
        path="C:\\Program Files\\MetaTrader 5\\terminal64.exe",  # Chemin vers MT5
        timeout=60000
    ):
        print("Erreur d'initialisation MT5")
        print(f"Code d'erreur: {mt5.last_error()}")
        return False
    
    # Vérifier la connexion
    if not mt5.terminal_info():
        print("Erreur: Impossible de se connecter au terminal")
        return False
    
    # Afficher les informations de connexion
    print("=== Connexion MT5 réussie ===")
    print(f"Version MT5: {mt5.version()}")
    print(f"Terminal: {mt5.terminal_info().name}")
    print(f"Compte: {mt5.account_info().login}")
    print(f"Balance: {mt5.account_info().balance}")
    print("===========================")
    
    return True

def get_market_data(symbol, timeframe, bars):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    if rates is None:
        return None
        
    # Création d'une liste de dictionnaires pour faciliter la conversion JSON
    candles = []
    for rate in rates:
        candle = {
            'time': rate[0],  # timestamp
            'open': rate[1],
            'high': rate[2],
            'low': rate[3],
            'close': rate[4],
            'volume': rate[5]
        }
        candles.append(candle)
        
    return candles

def send_data_to_api(symbol, candles, timeframe='M5'):
    payload = {
        'symbol': symbol,
        'timeframe': timeframe,
        'candles': candles
    }

    try:
        response = requests.post(
            CONFIG['api_url'],
            json=payload,
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code == 200:
            print(f"✅ {symbol} {timeframe} envoyé ({len(candles)} bougies)")
            return True
        else:
            print(f"❌ Erreur lors de l'envoi des données pour {symbol}: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Exception lors de l'envoi des données pour {symbol}: {str(e)}")
        return False

def main():
    print("""
██████╗  ██████╗ ████████╗    ████████╗██████╗  █████╗ ██████╗ ██╗███╗   ██╗ ██████╗ 
██╔══██╗██╔═══██╗╚══██╔══╝    ╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██║████╗  ██║██╔════╝ 
██████╔╝██║   ██║   ██║          ██║   ██████╔╝███████║██║  ██║██║██╔██╗ ██║██║  ███╗
██╔══██╗██║   ██║   ██║          ██║   ██╔══██╗██╔══██║██║  ██║██║██║╚██╗██║██║   ██║
██████╔╝╚██████╔╝   ██║          ██║   ██║  ██║██║  ██║██████╔╝██║██║ ╚████║╚██████╔╝
╚═════╝  ╚═════╝    ╚═╝          ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝ 
              PONT MT5 → CONSOLE DREVM (/api/market-data)
    """)
    
    print("Configuration:")
    print(f"• Paires surveillées: {', '.join(CONFIG['symbols'])}")
    print(f"• URL de l'API: {CONFIG['api_url']}")
    print(f"• Intervalle d'envoi: {CONFIG['send_interval']} secondes")
    print()
    
    # Vérifier si l'URL de l'API a été configurée
    if not CONFIG['api_url']:
        print("❌ ERREUR: définissez la variable d'environnement MARKET_DATA_API_URL")
        print("   (ex: MARKET_DATA_API_URL=http://localhost:8800/api/market-data)")
        return
    
    if not initialize_mt5():
        print("❌ Erreur d'initialisation de MetaTrader5")
        return
        
    try:
        while True:
            print(f"\n=== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
            for symbol in CONFIG['symbols']:
                for tf_const, tf_name, bars in CONFIG['timeframes']:
                    candles = get_market_data(symbol, tf_const, bars)
                    if candles:
                        send_data_to_api(symbol, candles, tf_name)
                    else:
                        print(f"❌ Données indisponibles : {symbol} {tf_name}")
            
            print(f"Attente de {CONFIG['send_interval']} secondes avant le prochain envoi...")
            time.sleep(CONFIG['send_interval'])
            
    except KeyboardInterrupt:
        print("\nArrêt du programme")
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    main() 