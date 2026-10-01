import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from app.services.alerts.user_delivery import accepts, deliver


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.user = SimpleNamespace(user_id='alice', quiet_hours_start=22, quiet_hours_end=7,
            quiet_hours_enabled=True, alert_high=True, min_expected_pips=10, require_high_confidence=True,
            discord_enabled=True, custom_discord_webhook='https://discord.com/api/webhooks/test',
            telegram_enabled=False, custom_telegram_token=None, custom_telegram_chat_id=None)
        self.prediction = {'symbol': 'XAUUSD', 'event': {'date': '2026-09-30', 'time': '09:30', 'event_name': 'CPI', 'currency': 'USD'},
            'prediction': {'risk_level': 'high', 'expected_movement_pips': 20, 'confidence': 'high', 'direction_probability': {'up': 60, 'down': 40}}}

    def test_quiet_hours_and_preferences(self):
        self.assertFalse(accepts(self.user, self.prediction, datetime(2026, 9, 30, 3, tzinfo=timezone.utc)))
        self.assertTrue(accepts(self.user, self.prediction, datetime(2026, 9, 30, 14, tzinfo=timezone.utc)))
        self.user.alert_high = False
        self.assertFalse(accepts(self.user, self.prediction, datetime(2026, 9, 30, 14, tzinfo=timezone.utc)))

    @patch('app.services.alerts.user_delivery.NotificationManager')
    @patch('app.services.alerts.user_delivery.release_alert')
    @patch('app.services.alerts.user_delivery.claim_alert', return_value='claim')
    def test_user_scoped_delivery_and_failed_retry(self, claim, release, manager):
        db = MagicMock()
        manager.return_value.send_predictive_alert.return_value = {'discord': False}
        deliver(db, self.user, self.prediction)
        self.assertEqual(claim.call_args.args[-1], 'alice:discord')
        release.assert_called_once_with(db, 'claim')
        db.add.assert_not_called()
        manager.return_value.send_predictive_alert.return_value = {'discord': True}
        deliver(db, self.user, self.prediction)
        self.assertEqual(db.add.call_args.args[0].user_id, 'alice')

    @patch('app.services.alerts.user_delivery.NotificationManager')
    def test_no_global_fallback(self, manager):
        self.user.custom_discord_webhook = None
        deliver(MagicMock(), self.user, self.prediction)
        manager.return_value.send_predictive_alert.assert_not_called()
