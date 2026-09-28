import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import AlertDeduplication, Base
from app.services.alerts.alert_deduplication import (
    build_alert_key,
    claim_alert,
    release_alert,
)


class AlertDeduplicationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.event = {
            "date": "2026-09-28",
            "time": "14:30",
            "currency": "USD",
            "event_name": "CPI",
        }

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_same_alert_is_claimed_only_once(self):
        first = claim_alert(self.session, self.event, "EURUSD", "predictive", "discord")
        second = claim_alert(self.session, self.event, "EURUSD", "predictive", "discord")

        self.assertEqual(first, build_alert_key(self.event, "EURUSD", "predictive", "discord"))
        self.assertIsNone(second)
        self.assertEqual(self.session.query(AlertDeduplication).count(), 1)

    def test_failed_delivery_can_be_retried(self):
        first = claim_alert(self.session, self.event, "EURUSD", "predictive", "discord")
        release_alert(self.session, first)
        second = claim_alert(self.session, self.event, "EURUSD", "predictive", "discord")

        self.assertIsNotNone(second)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
