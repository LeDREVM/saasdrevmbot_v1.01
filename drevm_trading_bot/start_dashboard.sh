#!/usr/bin/env bash
# Lance le dashboard NY Smart Money — http://localhost:8050
cd "$(dirname "$0")"
python3 -m uvicorn dashboard:app --port 8050
