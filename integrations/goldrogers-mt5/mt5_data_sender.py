import MetaTrader5 as mt5
import pandas as pd
import time
import requests
import json
from datetime import datetime
import os
import sys

# Configuration
CONFIG = {
    'symbols': ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'US30', 'XBRUSD'],
    'timeframe': mt5.TIMEFRAME_M5,
    'bars': 100,
    'send_interval': 300,  # 5 minutes
    'api_url': 'https://deuxy.xyz/api/market-data',
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

def send_data_to_api(symbol, candles):
    payload = {
        'symbol': symbol,
        'candles': candles
    }
    
    try:
        response = requests.post(
            CONFIG['api_url'], 
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            print(f"✅ Données pour {symbol} envoyées avec succès ({len(candles)} bougies)")
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
                           ENVOYEUR DE DONNÉES VERS HEROKU
    """)
    
    print("Configuration:")
    print(f"• Paires surveillées: {', '.join(CONFIG['symbols'])}")
    print(f"• URL de l'API: {CONFIG['api_url']}")
    print(f"• Intervalle d'envoi: {CONFIG['send_interval']} secondes")
    print()
    
    # Vérifier si l'URL de l'API a été configurée
    if CONFIG['api_url'] == 'https://votre-app-heroku.herokuapp.com/api/market-data':
        print("❌ ERREUR: Veuillez configurer l'URL de votre API Heroku dans le fichier.")
        print("Modifiez la valeur de 'api_url' dans la configuration.")
        return
    
    if not initialize_mt5():
        print("❌ Erreur d'initialisation de MetaTrader5")
        return
        
    try:
        while True:
            print(f"\n=== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
            for symbol in CONFIG['symbols']:
                candles = get_market_data(symbol, CONFIG['timeframe'], CONFIG['bars'])
                if candles:
                    send_data_to_api(symbol, candles)
                else:
                    print(f"❌ Impossible de récupérer les données pour {symbol}")
            
            print(f"Attente de {CONFIG['send_interval']} secondes avant le prochain envoi...")
            time.sleep(CONFIG['send_interval'])
            
    except KeyboardInterrupt:
        print("\nArrêt du programme")
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    main() 