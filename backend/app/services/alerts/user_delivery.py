"""Per-user delivery; no fallback to another account's notification channels."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from app.models.alert_settings import AlertLog
from app.services.alerts.alert_deduplication import claim_alert, release_alert
from app.services.alerts.notification_manager import NotificationManager


def accepts(user, prediction, now=None):
    hour = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo('America/Guadeloupe')).hour
    start, end = user.quiet_hours_start, user.quiet_hours_end
    quiet = start <= hour < end if start <= end else hour >= start or hour < end
    if user.quiet_hours_enabled and quiet:
        return False
    value = prediction['prediction']
    return (bool(getattr(user, 'alert_' + value['risk_level'], False))
            and value['expected_movement_pips'] >= user.min_expected_pips
            and (not user.require_high_confidence or value['confidence'] == 'high'))


def deliver(db, user, prediction):
    manager = NotificationManager(user.custom_discord_webhook, user.custom_telegram_token, user.custom_telegram_chat_id)
    channels = []
    if user.discord_enabled and user.custom_discord_webhook:
        channels.append('discord')
    if user.telegram_enabled and user.custom_telegram_token and user.custom_telegram_chat_id:
        channels.append('telegram')
    event, value = prediction['event'], prediction['prediction']
    for channel in channels:
        key = claim_alert(db, event, prediction['symbol'], 'predictive', f'{user.user_id}:{channel}')
        if not key:
            continue
        try:
            success = manager.send_predictive_alert(prediction, [channel]).get(channel, False)
        except Exception:
            release_alert(db, key)
            continue
        if not success:
            release_alert(db, key)
            continue
        db.add(AlertLog(user_id=user.user_id, event_name=event.get('event_name', event.get('event')),
            event_date=event['date'], event_time=event['time'], currency=event['currency'], symbol=prediction['symbol'],
            predicted_pips=value['expected_movement_pips'], predicted_direction=max(value['direction_probability'], key=value['direction_probability'].get),
            risk_level=value['risk_level'], confidence=value['confidence'], channels_sent=[channel], delivery_status='sent'))
        db.commit()
