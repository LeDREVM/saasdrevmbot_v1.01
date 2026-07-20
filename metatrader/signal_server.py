"""
Signal Server — reçoit les signaux de n8n et les transmet à MT5 via socket.
Lance ce script sur le VPS (même machine que n8n).
MT5 EA se connecte en local sur MT5_BRIDGE_PORT.
"""

import asyncio
import json
import logging
import os
import socket
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
log = logging.getLogger(__name__)

HTTP_PORT    = int(os.getenv('MT5_SERVER_PORT', 5000))
BRIDGE_PORT  = int(os.getenv('MT5_BRIDGE_PORT', 5001))   # socket EA ↔ Python
SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY', '')

pending_signals: list[dict] = []
pending_lock = threading.Lock()


# ─── Socket bridge (EA se connecte ici) ──────────────────────────────────────

def bridge_server():
    """Serveur TCP que l'EA MT5 poll toutes les secondes."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('0.0.0.0', BRIDGE_PORT))
    srv.listen(5)
    log.info(f"[Bridge] Listening on port {BRIDGE_PORT}")

    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_ea, args=(conn, addr), daemon=True).start()


def handle_ea(conn: socket.socket, addr):
    log.info(f"[Bridge] EA connected from {addr}")
    try:
        with pending_lock:
            signal = pending_signals.pop(0) if pending_signals else None

        if signal:
            msg = json.dumps(signal) + '\n'
            conn.sendall(msg.encode())
            log.info(f"[Bridge] Sent signal: {signal.get('symbol')} {signal.get('direction')} score={signal.get('score')}")
            # recv() hors du lock : l'EA peut prendre du temps, on ne bloque plus les threads HTTP
            ack = conn.recv(256).decode().strip()
            log.info(f"[Bridge] EA ack: {ack}")
            update_signal_status(signal.get('signal_id'), ack)
        else:
            conn.sendall(b'NONE\n')
    except Exception as e:
        log.error(f"[Bridge] {e}")
    finally:
        conn.close()


def update_signal_status(signal_id: str, ack: str):
    if not SUPABASE_URL or not signal_id:
        return
    try:
        ticket = None
        if ack.startswith('ACK:'):
            ticket = int(ack.split(':')[1])
        payload = {'status': 'EXECUTED' if ticket else 'SENT', 'sent_at': datetime.now(timezone.utc).isoformat()}
        if ticket:
            payload['mt5_ticket'] = ticket
        requests.patch(
            f"{SUPABASE_URL}/rest/v1/trade_signals?id=eq.{signal_id}",
            headers={
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json',
                'Prefer': 'return=minimal'
            },
            json=payload,
            timeout=5
        )
    except Exception as e:
        log.error(f"[Supabase update] {e}")


# ─── HTTP receiver (n8n → Python) ────────────────────────────────────────────

class SignalHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == '/health':
            self._respond(200, {'status': 'ok', 'pending': len(pending_signals)})
        else:
            self._respond(404, {'error': 'not found'})

    def do_POST(self):
        if self.path != '/signal':
            self._respond(404, {'error': 'not found'})
            return

        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)

        try:
            signal = json.loads(body)
        except json.JSONDecodeError as e:
            self._respond(400, {'error': str(e)})
            return

        required = ['symbol', 'direction', 'entry_price', 'stop_loss', 'take_profit']
        missing = [f for f in required if f not in signal]
        if missing:
            self._respond(400, {'error': f'missing fields: {missing}'})
            return

        signal['received_at'] = datetime.now(timezone.utc).isoformat()
        with pending_lock:
            pending_signals.append(signal)

        log.info(f"[HTTP] Signal queued: {signal['symbol']} {signal['direction']} score={signal.get('score')}")
        self._respond(200, {'status': 'queued', 'queue_depth': len(pending_signals)})

    def _respond(self, code: int, data: dict):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # silence default HTTP logs


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    bridge_thread = threading.Thread(target=bridge_server, daemon=True)
    bridge_thread.start()

    http_srv = HTTPServer(('0.0.0.0', HTTP_PORT), SignalHandler)
    log.info(f"[HTTP] Signal server on port {HTTP_PORT}")
    http_srv.serve_forever()
