#!/bin/bash

echo "========================================"
echo "Voice Assistant Status"
echo "========================================"
echo ""

# Check voice_core service
echo "Voice Core Service:"
systemctl is-active voice_core 2>/dev/null && echo "  Status: RUNNING" || echo "  Status: STOPPED"
systemctl is-enabled voice_core 2>/dev/null && echo "  Enabled: YES" || echo "  Enabled: NO"
echo ""

# Check orchestrator service
echo "Orchestrator Service:"
systemctl is-active orchestrator 2>/dev/null && echo "  Status: RUNNING" || echo "  Status: STOPPED"
systemctl is-enabled orchestrator 2>/dev/null && echo "  Enabled: YES" || echo "  Enabled: NO"
echo ""

# Check Ollama
echo "Ollama Service:"
if systemctl is-active ollama &>/dev/null; then
    echo "  Status: RUNNING"
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "  API: RESPONDING"
        # List models
        echo "  Models:"
        curl -s http://localhost:11434/api/tags | python3 -c "import sys, json; [print(f\"    - {m['name']}\") for m in json.load(sys.stdin).get('models', [])]" 2>/dev/null || echo "    (unable to list)"
    else
        echo "  API: NOT RESPONDING"
    fi
else
    echo "  Status: STOPPED"
fi
echo ""

# Check IPC socket
echo "IPC Socket:"
if [ -S "/tmp/voice_assistant.sock" ]; then
    echo "  Status: EXISTS"
else
    echo "  Status: NOT FOUND"
fi
echo ""

# Check logs
echo "Recent Errors (last 10):"
journalctl -u voice_core -u orchestrator --no-pager -n 10 --grep "ERROR" 2>/dev/null || echo "  None found"
echo ""

echo "========================================"
echo "To view live logs:"
echo "  journalctl -u voice_core -f"
echo "  journalctl -u orchestrator -f"
echo "========================================"
