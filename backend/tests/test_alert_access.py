import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.core.alert_auth import require_alert_owner
from fastapi import Depends
from app.api.routes import alert_config
from app.core.database import get_db
from types import SimpleNamespace


class AccessTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        @app.get('/settings/{user_id}', dependencies=[Depends(require_alert_owner)])
        def endpoint(user_id):
            return {'id': user_id}
        self.client = TestClient(app)

    def test_missing_token(self):
        self.assertEqual(self.client.get('/settings/alice').status_code, 401)

    def test_server_auth_unconfigured_fails_closed(self):
        with patch.dict(os.environ, {'SUPABASE_URL': '', 'SUPABASE_ANON_KEY': ''}):
            self.assertEqual(self.client.get('/settings/alice', headers={'Authorization': 'Bearer fake'}).status_code, 503)

    def test_other_users_forbidden(self):
        import httpx
        response = httpx.Response(200, json={'id': 'alice'}, request=httpx.Request('GET', 'https://example.com'))
        with patch.dict(os.environ, {'SUPABASE_URL': 'https://example.com', 'SUPABASE_ANON_KEY': 'public'}), patch('httpx.AsyncClient.get', new=AsyncMock(return_value=response)):
            headers = {'Authorization': 'Bearer test'}
            self.assertEqual(self.client.get('/settings/alice', headers=headers).status_code, 200)
            self.assertEqual(self.client.get('/settings/bob', headers=headers).status_code, 403)

    def test_invalid_and_unavailable_auth(self):
        import httpx
        headers = {'Authorization': 'Bearer fake'}
        with patch.dict(os.environ, {'SUPABASE_URL': 'https://example.com', 'SUPABASE_ANON_KEY': 'public'}):
            invalid = httpx.Response(401, request=httpx.Request('GET', 'https://example.com'))
            with patch('httpx.AsyncClient.get', new=AsyncMock(return_value=invalid)):
                self.assertEqual(self.client.get('/settings/alice', headers=headers).status_code, 401)
            with patch('httpx.AsyncClient.get', new=AsyncMock(side_effect=httpx.TimeoutException('timeout'))):
                self.assertEqual(self.client.get('/settings/alice', headers=headers).status_code, 503)

    def test_real_routes_protected_and_secrets_masked(self):
        app = FastAPI()
        app.include_router(alert_config.router)
        client = TestClient(app)
        for path in ['settings', 'history', 'stats', 'active-alerts']:
            self.assertEqual(client.get(f'/alert-config/{path}/alice').status_code, 401)
        self.assertEqual(client.patch('/alert-config/settings/alice', json={}).status_code, 401)
        self.assertEqual(client.post('/alert-config/test-alert/alice').status_code, 401)
        user = SimpleNamespace(user_id='alice', watched_symbols=['XAUUSD'], alert_extreme=True, alert_high=True,
            alert_medium=False, discord_enabled=True, telegram_enabled=True, custom_discord_webhook='private-webhook',
            custom_telegram_token='private-token', custom_telegram_chat_id='123', quiet_hours_enabled=False,
            quiet_hours_start=22, quiet_hours_end=7, advance_notice_hours=2, min_expected_pips=10,
            require_high_confidence=False, updated_at=None)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = user
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_alert_owner] = lambda: 'alice'
        response = client.get('/alert-config/settings/alice')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('private-token', response.text)
        self.assertNotIn('private-webhook', response.text)
        self.assertTrue(response.json()['custom_webhooks']['telegram_configured'])

    def test_preferences_validate_numbers_and_webhook(self):
        from pydantic import ValidationError
        for body in [{'quiet_hours_start': 25}, {'min_expected_pips': float('nan')}, {'watched_symbols': None},
                     {'custom_discord_webhook': 'http://127.0.0.1/internal'}]:
            with self.assertRaises(ValidationError):
                alert_config.AlertSettingsUpdate(**body)
