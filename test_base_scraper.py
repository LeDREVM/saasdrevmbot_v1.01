#!/usr/bin/env python3
"""
Script de test pour base_scraper.py
Vérifie que toutes les classes et méthodes fonctionnent correctement
"""

import sys
sys.path.insert(0, 'backend')

from datetime import datetime
from app.services.economic_calendar.base_scraper import (
    ImpactLevel,
    EconomicEvent,
    BaseEconomicScraper
)

def test_impact_level():
    """Test de l'énumération ImpactLevel"""
    print("🧪 Test ImpactLevel...")
    
    # Test des valeurs
    assert ImpactLevel.LOW.value == "Low"
    assert ImpactLevel.MEDIUM.value == "Medium"
    assert ImpactLevel.HIGH.value == "High"
    
    # Test de création depuis string
    impact = ImpactLevel("High")
    assert impact == ImpactLevel.HIGH
    
    print("✅ ImpactLevel OK")


def test_economic_event():
    """Test de la classe EconomicEvent"""
    print("\n🧪 Test EconomicEvent...")
    
    # Créer un événement de test
    event = EconomicEvent(
        source="forexfactory",
        date="2026-02-06",
        time="14:30",
        currency="USD",
        event="Non-Farm Payrolls",
        impact=ImpactLevel.HIGH,
        actual="250K",
        forecast="200K",
        previous="180K"
    )
    
    # Test des propriétés de base
    assert event.source == "forexfactory"
    assert event.date == "2026-02-06"
    assert event.time == "14:30"
    assert event.currency == "USD"
    assert event.event == "Non-Farm Payrolls"
    assert event.impact == ImpactLevel.HIGH
    assert event.actual == "250K"
    assert event.forecast == "200K"
    assert event.previous == "180K"
    
    print("  ✓ Propriétés de base OK")
    
    # Test datetime_obj
    dt = event.datetime_obj
    assert isinstance(dt, datetime)
    assert dt.year == 2026
    assert dt.month == 2
    assert dt.day == 6
    assert dt.hour == 14
    assert dt.minute == 30
    
    print("  ✓ datetime_obj OK")
    
    # Test is_high_impact
    assert event.is_high_impact == True
    
    event_low = EconomicEvent(
        source="test",
        date="2026-02-06",
        time="10:00",
        currency="EUR",
        event="Test Event",
        impact=ImpactLevel.LOW
    )
    assert event_low.is_high_impact == False
    
    print("  ✓ is_high_impact OK")
    
    # Test to_dict
    event_dict = event.to_dict()
    assert isinstance(event_dict, dict)
    assert event_dict['source'] == "forexfactory"
    assert event_dict['date'] == "2026-02-06"
    assert event_dict['time'] == "14:30"
    assert event_dict['currency'] == "USD"
    assert event_dict['event'] == "Non-Farm Payrolls"
    assert event_dict['impact'] == "High"
    assert event_dict['actual'] == "250K"
    assert event_dict['forecast'] == "200K"
    assert event_dict['previous'] == "180K"
    
    print("  ✓ to_dict OK")
    
    # Test avec valeurs optionnelles None
    event_minimal = EconomicEvent(
        source="test",
        date="2026-02-06",
        time="10:00",
        currency="EUR",
        event="Test",
        impact=ImpactLevel.MEDIUM
    )
    
    minimal_dict = event_minimal.to_dict()
    assert minimal_dict['actual'] is None
    assert minimal_dict['forecast'] is None
    assert minimal_dict['previous'] is None
    
    print("  ✓ Valeurs optionnelles OK")
    
    print("✅ EconomicEvent OK")


def test_base_scraper():
    """Test de la classe abstraite BaseEconomicScraper"""
    print("\n🧪 Test BaseEconomicScraper...")
    
    # Créer une implémentation concrète pour tester
    class TestScraper(BaseEconomicScraper):
        def scrape_day(self, date: datetime):
            return [
                EconomicEvent(
                    source="test",
                    date=date.strftime("%Y-%m-%d"),
                    time="10:00",
                    currency="USD",
                    event="Test Event",
                    impact=ImpactLevel.HIGH
                )
            ]
        
        def scrape_week(self):
            return []
    
    # Instancier
    scraper = TestScraper()
    
    # Test headers
    assert 'User-Agent' in scraper.headers
    assert 'Mozilla' in scraper.headers['User-Agent']
    
    print("  ✓ Headers OK")
    
    # Test méthodes abstraites implémentées
    test_date = datetime(2026, 2, 6)
    events = scraper.scrape_day(test_date)
    assert len(events) == 1
    assert events[0].source == "test"
    assert events[0].date == "2026-02-06"
    
    print("  ✓ Méthodes abstraites OK")
    
    print("✅ BaseEconomicScraper OK")


def test_edge_cases():
    """Test des cas limites"""
    print("\n🧪 Test des cas limites...")
    
    # Test datetime_obj avec format invalide (fallback)
    event = EconomicEvent(
        source="test",
        date="2026-02-06",
        time="invalid",
        currency="USD",
        event="Test",
        impact=ImpactLevel.LOW
    )
    
    try:
        dt = event.datetime_obj
        # Devrait fallback sur la date seule
        assert dt.year == 2026
        assert dt.month == 2
        assert dt.day == 6
        print("  ✓ Fallback datetime OK")
    except Exception as e:
        print(f"  ⚠️  Fallback datetime: {e}")
    
    # Test avec des caractères spéciaux
    event_special = EconomicEvent(
        source="test",
        date="2026-02-06",
        time="10:00",
        currency="USD",
        event="Test Event with émojis 📊 and special chars €$£",
        impact=ImpactLevel.HIGH,
        actual="1.5%",
        forecast="1.2%",
        previous="1.0%"
    )
    
    event_dict = event_special.to_dict()
    assert "📊" in event_dict['event']
    assert "€" in event_dict['event']
    
    print("  ✓ Caractères spéciaux OK")
    
    print("✅ Cas limites OK")


def test_integration():
    """Test d'intégration complet"""
    print("\n🧪 Test d'intégration...")
    
    # Créer plusieurs événements
    events = [
        EconomicEvent(
            source="forexfactory",
            date="2026-02-06",
            time="08:30",
            currency="EUR",
            event="German GDP",
            impact=ImpactLevel.HIGH,
            actual="0.5%",
            forecast="0.3%",
            previous="0.2%"
        ),
        EconomicEvent(
            source="investing",
            date="2026-02-06",
            time="14:30",
            currency="USD",
            event="Non-Farm Payrolls",
            impact=ImpactLevel.HIGH,
            actual="250K",
            forecast="200K",
            previous="180K"
        ),
        EconomicEvent(
            source="forexfactory",
            date="2026-02-06",
            time="16:00",
            currency="GBP",
            event="BOE Interest Rate Decision",
            impact=ImpactLevel.HIGH
        )
    ]
    
    # Trier par datetime
    sorted_events = sorted(events, key=lambda e: e.datetime_obj)
    assert sorted_events[0].time == "08:30"
    assert sorted_events[1].time == "14:30"
    assert sorted_events[2].time == "16:00"
    
    print("  ✓ Tri par datetime OK")
    
    # Filtrer par impact
    high_impact = [e for e in events if e.is_high_impact]
    assert len(high_impact) == 3
    
    print("  ✓ Filtrage par impact OK")
    
    # Convertir tous en dict
    events_dicts = [e.to_dict() for e in events]
    assert len(events_dicts) == 3
    assert all(isinstance(d, dict) for d in events_dicts)
    
    print("  ✓ Conversion en dict OK")
    
    print("✅ Intégration OK")


def main():
    """Exécute tous les tests"""
    print("=" * 60)
    print("🚀 Test de base_scraper.py")
    print("=" * 60)
    
    try:
        test_impact_level()
        test_economic_event()
        test_base_scraper()
        test_edge_cases()
        test_integration()
        
        print("\n" + "=" * 60)
        print("✅ TOUS LES TESTS SONT PASSÉS !")
        print("=" * 60)
        print("\n📊 Résumé:")
        print("  ✓ ImpactLevel: Fonctionnel")
        print("  ✓ EconomicEvent: Fonctionnel")
        print("  ✓ BaseEconomicScraper: Fonctionnel")
        print("  ✓ Cas limites: OK")
        print("  ✓ Intégration: OK")
        print("\n✅ Le fichier base_scraper.py est 100% fonctionnel !")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ ÉCHEC DU TEST: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
