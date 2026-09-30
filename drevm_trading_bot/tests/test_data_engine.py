"""Offline regression tests: python -m unittest discover -s drevm_trading_bot/tests."""
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import pandas as pd
import requests

SPEC = importlib.util.spec_from_file_location(
    "data_engine", Path(__file__).resolve().parents[1] / "data_engine.py"
)
engine = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(engine)


def candle(time="2026-09-30 13:30:00", **changes):
    row = dict(datetime=time, open="10", high="12", low="9", close="11", volume="50")
    row.update(changes)
    return row


class DataEngineTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {"TWELVEDATA_API_KEY": "test-secret"})
        env.start()
        self.addCleanup(env.stop)
        get = patch.object(engine.requests, "get")
        self.get = get.start()
        self.addCleanup(get.stop)
        self.response = Mock()
        self.get.return_value = self.response

    def fetch(self, values, interval="5min"):
        self.response.json.return_value = {"status": "ok", "values": values}
        return engine.get_data("EUR/USD", interval)

    def test_clean_numeric_chronological_unique_and_index(self):
        df = self.fetch([candle("2026-09-30 13:35:00"), candle(), candle(close="10")])
        self.assertEqual(list(df.columns), ["datetime", "open", "high", "low", "close", "volume"])
        self.assertEqual(list(df.index), [0, 1])
        self.assertTrue(df.datetime.is_monotonic_increasing)
        self.assertTrue(df.datetime.is_unique)
        self.assertEqual(str(df.datetime.dt.tz), "UTC")
        self.assertEqual(df.close.iloc[0], 11.0)
        for col in ["open", "high", "low", "close", "volume"]:
            self.assertEqual(df[col].dtype, "float64")

    def test_aliases_and_existing_intervals(self):
        for alias, expected in [("H4", "4h"), ("m15", "15min"), ("M5", "5min"),
                                ("4h", "4h"), ("15min", "15min"), ("1h", "1h")]:
            with self.subTest(interval=alias):
                self.fetch([candle()], alias)
                args, kwargs = self.get.call_args
                self.assertEqual(args, ("https://api.twelvedata.com/time_series",))
                self.assertEqual(kwargs["params"]["interval"], expected)
                self.assertEqual(kwargs["params"]["timezone"], "UTC")
                self.assertEqual(kwargs["params"]["outputsize"], 200)
                self.assertEqual(kwargs["timeout"], (5, 15))

    def test_missing_and_invalid_volume_are_not_zero(self):
        rows = [candle(volume=None), candle("2026-09-30 13:35:00", volume="bad"),
                candle("2026-09-30 13:40:00", volume="-1"),
                candle("2026-09-30 13:45:00", volume="inf")]
        self.assertTrue(self.fetch(rows).volume.isna().all())
        row = candle()
        del row["volume"]
        self.assertTrue(self.fetch([row]).volume.isna().all())

    def test_bad_rows_dropped_before_deduplication(self):
        rows = [candle(close=None), candle(), candle("bad"), candle(high="8"),
                candle(low="12"), candle(open="inf"), candle(open="0"),
                candle(close="text"), candle(low=None)]
        with self.assertLogs(engine.LOGGER, "WARNING"):
            df = self.fetch(rows)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.close.iloc[0], 11.0)

    def test_malformed_api_responses(self):
        payloads = [None, [], {"status": "error", "code": 429, "message": "test-secret"},
                    {"status": "error", "values": [candle()]}, {"values": []}, {},
                    {"values": {}}, {"values": [None]}, {"values": [{"close": "10"}]}]
        for payload in payloads:
            with self.subTest(payload=payload):
                self.response.json.return_value = payload
                with self.assertRaises(engine.DataEngineError) as caught:
                    engine.get_data("EUR/USD")
                self.assertNotIn("test-secret", str(caught.exception))

    def test_all_invalid_rows_fail(self):
        with self.assertLogs(engine.LOGGER, "WARNING"):
            with self.assertRaises(engine.DataEngineError):
                self.fetch([candle(close="bad")])

    def test_timeout_and_network_errors_hide_credentials(self):
        for exception in [requests.Timeout, requests.ConnectionError, requests.HTTPError]:
            with self.subTest(exception=exception):
                self.get.side_effect = exception("url?apikey=test-secret")
                with self.assertRaises(engine.DataEngineError) as caught:
                    engine.get_data("EUR/USD")
                self.assertNotIn("test-secret", str(caught.exception))
                self.assertTrue(caught.exception.__suppress_context__)

    def test_http_status_checked_before_json(self):
        self.response.raise_for_status.side_effect = requests.HTTPError("401 test-secret")
        with self.assertRaises(engine.DataEngineError):
            engine.get_data("EUR/USD")
        self.response.json.assert_not_called()

    def test_invalid_json(self):
        self.response.json.side_effect = ValueError("test-secret")
        with self.assertRaises(engine.DataEngineError):
            engine.get_data("EUR/USD")

    def test_bad_inputs_do_not_call_api(self):
        for symbol, interval in [("", "M5"), (None, "M5"), ("A,B", "M5"),
                                 ("EUR/USD", "M2"), ("EUR/USD", None)]:
            with self.subTest(symbol=symbol, interval=interval):
                with self.assertRaises(ValueError):
                    engine.get_data(symbol, interval)
        self.get.assert_not_called()

    def test_missing_key_does_not_call_api(self):
        for key in ["", " ", "YOUR_TWELVEDATA_KEY"]:
            with patch.dict(os.environ, {"TWELVEDATA_API_KEY": key}):
                with self.assertRaises(engine.DataEngineError):
                    engine.get_data("EUR/USD")
        self.get.assert_not_called()

    def test_provider_without_status_and_zero_volume(self):
        self.response.json.return_value = {"values": [candle(volume="0")]}
        self.assertEqual(engine.get_data("EUR/USD").volume.iloc[0], 0.0)


if __name__ == "__main__":
    unittest.main()
