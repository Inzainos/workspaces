#!/bin/bash
echo "--- Starting API ---"
python3 -m uvicorn sentinel_omega.infrastructure.dashboard.api:app --host 0.0.0.0 --port 8787 > api_log.txt 2>&1 &
echo "--- Starting Frontend ---"
cd /home/deamon/workspaces/sentinel_omega/infrastructure/dashboard/web && { npm run dev -- --host 0.0.0.0 > web_log.txt 2>&1 & }
echo "Waiting for stabilization..."
sleep 10
echo "--- API Log ---"
cat api_log.txt
echo "--- Web Log ---"
cat web_log.txt
ss -tulpn | grep -E '8787|5173'
