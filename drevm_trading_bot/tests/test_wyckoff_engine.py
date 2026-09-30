import importlib.util
from pathlib import Path
import unittest

import pandas as pd

SPEC = importlib.util.spec_from_file_location(
    "wyckoff_engine", Path(__file__).resolve().parents[1] / "wyckoff_engine.py"
)
engine = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(engine)


def frame(sweep=None, confirmation=None):
    history = [dict(high=110, low=100, close=105) for _ in range(20)]
    return pd.DataFrame(history + [
        sweep or dict(high=106, low=98, close=103),
        confirmation or dict(high=109, low=102, close=108),
    ])


class WyckoffTests(unittest.TestCase):
    def test_spring_and_no_mutation(self):
        df = frame()
        original = df.copy(deep=True)
        self.assertEqual(engine.detect_wyckoff(df), "SPRING")
        pd.testing.assert_frame_equal(df, original)

    def test_utad(self):
        df = frame(dict(high=112, low=104, close=108),
                   dict(high=109, low=101, close=102))
        self.assertEqual(engine.detect_wyckoff(df), "UTAD")

    def test_sweep_alone_is_not_signal(self):
        self.assertIsNone(engine.detect_wyckoff(frame().iloc[:-1]))

    def test_no_confirmation_or_wick_only_confirmation(self):
        for close in [104, 106]:
            self.assertIsNone(engine.detect_wyckoff(frame(
                confirmation=dict(high=109, low=102, close=close))))

    def test_no_sweep_and_boundary_touch(self):
        for low in [100, 101]:
            self.assertIsNone(engine.detect_wyckoff(frame(
                sweep=dict(high=106, low=low, close=103))))

    def test_no_reintegration_and_boundary_close(self):
        for close in [99, 100, 110]:
            self.assertIsNone(engine.detect_wyckoff(frame(
                sweep=dict(high=110, low=98, close=close))))

    def test_two_sided_sweep_rejected(self):
        self.assertIsNone(engine.detect_wyckoff(frame(
            sweep=dict(high=112, low=98, close=103),
            confirmation=dict(high=115, low=102, close=114))))

    def test_spring_extreme_retested_or_broken(self):
        for low in [98, 97]:
            self.assertIsNone(engine.detect_wyckoff(frame(
                confirmation=dict(high=109, low=low, close=108))))

    def test_utad_strict_confirmation_and_invalidation(self):
        sweep = dict(high=112, low=104, close=108)
        for confirmation in [dict(high=109, low=101, close=104),
                             dict(high=113, low=101, close=102),
                             dict(high=112, low=101, close=102)]:
            self.assertIsNone(engine.detect_wyckoff(frame(sweep, confirmation)))

    def test_insufficient_and_bad_input(self):
        for df in [None, [], pd.DataFrame(), frame().iloc[:21],
                   frame().drop(columns="high")]:
            self.assertIsNone(engine.detect_wyckoff(df))

    def test_bad_prices_rejected(self):
        for value in [None, "bad", float("inf"), -1, 0]:
            df = frame()
            df["low"] = df["low"].astype(object)
            df.loc[10, "low"] = value
            self.assertIsNone(engine.detect_wyckoff(df))
        df = frame()
        df.loc[10, "close"] = 120
        self.assertIsNone(engine.detect_wyckoff(df))

    def test_numeric_strings_and_arbitrary_index(self):
        df = frame().astype(str)
        df.index = range(100, 122)
        self.assertEqual(engine.detect_wyckoff(df), "SPRING")

    def test_no_repeat_on_following_candle(self):
        df = pd.concat([frame(), pd.DataFrame([dict(high=110, low=106, close=109)])],
                       ignore_index=True)
        self.assertIsNone(engine.detect_wyckoff(df))

    def test_range_excludes_sweep_and_confirmation(self):
        self.assertEqual(engine.detect_wyckoff(frame()), "SPRING")
        df = frame()
        df.loc[0, "low"] = 97
        self.assertIsNone(engine.detect_wyckoff(df))


if __name__ == "__main__":
    unittest.main()
