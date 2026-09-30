"""Offline tests for local scoring, routes and atomic history."""
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import scoring
from app.services.ai import scoring_store
from app.services.ai.scoring_contract import score_local, validate_result, ScoringError


def context():
    return {"symbol": "US30", "direction": "BUY", "setup_grade": "A+", "htf_phase": "markup",
            "session_active": True, "spread_ok": True, "news_checked": True,
            "confluence": {"wyckoff": "SPRING", "confirmed": True, "rsi_aligned": True,
                           "price_above_kijun": True, "m15_zone_touched": True, "m5_confirmed": True}}


class LocalScoringTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "history.json"
        p = patch.object(scoring_store, "_STORE_PATH", self.path)
        p.start()
        self.addCleanup(p.stop)
        app = FastAPI()
        app.include_router(scoring.router, prefix="/api")
        self.client = TestClient(app)

    def test_aligned_score_with_traceable_criteria(self):
        result = score_local(context())
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["recommendation"], "TRADE")
        self.assertEqual(sum(c["points"] for c in result["technical_baseline"]["criteria"]), 100)
        self.assertEqual(result["provider"], "local")

    def test_missing_confirmation_or_news_never_trade(self):
        for change in ["confirmed", "m5_confirmed", "news_checked", "spread_ok", "session_active"]:
            ctx = context()
            if change in ctx:
                ctx[change] = False
            else:
                ctx["confluence"][change] = False
            self.assertNotEqual(score_local(ctx)["recommendation"], "TRADE")

    def test_imminent_event_wait(self):
        ctx = context()
        ctx["event_context"] = {"minutes_until": 5}
        self.assertEqual(score_local(ctx)["recommendation"], "WAIT")

    def test_wrong_side_gets_no_wyckoff_or_kijun_bonus(self):
        ctx = context()
        ctx["direction"] = "SELL"
        result = score_local(ctx)
        self.assertEqual(result["score"], 60)
        self.assertEqual(result["recommendation"], "WAIT")

    def test_sparse_context_skip(self):
        result = score_local({"symbol": "US30", "setup_grade": "C", "direction": "BUY"})
        self.assertEqual(result["score"], 5)
        self.assertEqual(result["recommendation"], "SKIP")

    def test_validation_rejects_bad_provider_history(self):
        for value in [True, "75", -1, 101, float("nan"), float("inf")]:
            with self.assertRaises(ScoringError):
                validate_result({"score": value, "recommendation": "WAIT", "reasoning": "Test"})

    def test_local_route_does_not_call_external_services(self):
        with patch("requests.post", side_effect=AssertionError("External call forbidden")), \
             patch("requests.get", side_effect=AssertionError("External call forbidden")):
            self.assertFalse(self.client.get("/api/scoring/status").json()["external_calls"])
            response = self.client.post("/api/scoring/analyze", json=context())
            self.assertEqual(response.status_code, 200)
            result = response.json()
            self.assertIn("id", result)
            self.assertTrue(result["generated_at"].endswith("+00:00"))
            history = self.client.get("/api/scoring/history?limit=50").json()
            self.assertEqual(history["count"], 1)
            self.assertEqual(self.client.get("/api/scoring/stats").json()["total"], 1)

    def test_invalid_inputs_and_notifications_rejected(self):
        for changes in [{"direction": "HOLD"}, {"symbol": "<script>"}, {"setup_grade": "X"},
                        {"event_context": {"minutes_until": -1}}, {"notify": True}]:
            response = self.client.post("/api/scoring/analyze", json={**context(), **changes})
            self.assertEqual(response.status_code, 422)
        self.assertFalse(self.path.exists())

    def test_atomic_concurrent_persistence(self):
        result = score_local(context())
        with ThreadPoolExecutor(max_workers=4) as pool:
            entries = list(pool.map(lambda _: scoring_store.save_score(result), range(12)))
        history = scoring_store.load_scores()
        self.assertEqual(len(history), 12)
        self.assertEqual(len({s["id"] for s in history}), 12)
        self.assertEqual({s["id"] for s in history}, {s["id"] for s in entries})

    def test_corrupt_history_is_not_overwritten(self):
        self.path.write_text("broken json", encoding="utf-8")
        response = self.client.post("/api/scoring/analyze", json=context())
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.path.read_text(), "broken json")
        self.assertEqual(self.client.get("/api/scoring/history").status_code, 503)

    def test_write_failure_never_claims_success(self):
        with patch.object(scoring_store.os, "replace", side_effect=OSError("disk full")):
            self.assertEqual(self.client.post("/api/scoring/analyze", json=context()).status_code, 503)
        self.assertFalse(self.path.exists())

    def test_bounds_and_stats_filter_legacy_invalid_entries(self):
        with patch.object(scoring_store, "_MAX_ENTRIES", 2):
            for _ in range(3):
                scoring_store.save_score(score_local(context()))
        self.assertEqual(len(scoring_store.load_scores()), 2)
        data = json.loads(self.path.read_text()) + [{"score": "invalid"}]
        self.path.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(scoring_store.get_stats()["invalid_entries"], 1)
        self.assertEqual(self.client.get("/api/scoring/history?limit=0").status_code, 422)


if __name__ == "__main__":
    unittest.main()
