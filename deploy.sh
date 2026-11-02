#!/usr/bin/env bash
# StudyBuddy EC2 deploy: venv + deps + live Bedrock check + start Web UI.
# Assumes the repo is cloned at ~/studybuddy and an IAM role with
# bedrock:InvokeModel is attached to the instance.
set -e
cd "$HOME/studybuddy"
python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
echo "=== LIVE CHECK (real Bedrock call via the Tutor agent) ==="
.venv/bin/python app.py --mode live 2>&1 | tail -45
echo "=== START WEB UI on :8080 ==="
pkill -f "web/server.py" 2>/dev/null || true
STUDYBUDDY_MODE=live PORT=8080 nohup .venv/bin/python web/server.py > /tmp/sb-web.log 2>&1 &
sleep 4
curl -s http://localhost:8080/api/lessons
echo
echo "=== DEPLOY DONE ==="
