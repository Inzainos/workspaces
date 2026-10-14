#!/bin/bash
# Clean logs
rm -f /home/deamon/api_debug.log /home/deamon/web_debug.log

# Start API with full traceback and unbuffered output
# Using the full path to python and uvicorn
/home/deamon/workspaces/.venv/bin/python3 -u -m uvicorn sentinel_omega.infrastructure.dashboard.api:app --host 0.0.0.0 --port 8787 > /home/deamon/api_debug.log 2>&1 &
API_PID=$!

# Start Frontend
cd /home/deamon/workspaces/sentinel_omega/infrastructure/dashboard/web
/home/deamon/workspaces/.venv/bin/npm run dev -- --host 0.0.0.0 > /home/deamon/web_debug.log 2>&1 &
WEB_PID=$!

echo "Processes started. API: $API_PID, WEB: $WEB_PID"
sleep 5

echo "--- API LOG ---"
cat /home/deamon/api_debug.log
echo "--- WEB LOG ---"
cat /home/deamon/web_debug.log
echo "--- PORTS ---"
ss -tulpn | grep -E '8787|517'
