import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import trading_economics


class TradingEconomicsRouteTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(trading_economics.router, prefix="/trading-economics")
        self.client = TestClient(app)

    def test_today_rejects_invalid_impact(self):
        with patch.object(trading_economics, "get_cached_events", return_value=[]):
            response = self.client.get("/trading-economics/today", params={"impact": "explique"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("Impact invalide", response.json()["detail"])

    def test_upcoming_does_not_mutate_cached_events(self):
        event = {
            "date": (datetime.now() + timedelta(minutes=10)).isoformat(),
            "time": "10:00",
            "currency": "USD",
            "impact": "high",
            "event": "CPI"
        }

        with patch.object(trading_economics, "get_cached_events", return_value=[event]):
            response = self.client.get("/trading-economics/upcoming", params={"minutes": 30})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 1)
        self.assertIn("minutes_until", body["events"][0])
        self.assertNotIn("minutes_until", event)

    def test_upcoming_rejects_non_positive_minutes(self):
        response = self.client.get("/trading-economics/upcoming", params={"minutes": 0})

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
