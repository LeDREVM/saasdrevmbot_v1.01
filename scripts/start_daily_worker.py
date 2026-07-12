"""
Script pour démarrer le worker de calendrier économique quotidien
"""

import sys
import os

# Ajouter le chemin backend au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.workers.daily_calendar_worker import main

if __name__ == "__main__":
    main()
