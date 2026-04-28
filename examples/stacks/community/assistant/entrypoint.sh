#!/bin/bash
set -e

echo "🌱 Initializing Nursery Assistant..."

# Wait for Frappe to be ready
echo "Waiting for Frappe API..."
until curl -f http://frappe:8000/api/method/ping 2>/dev/null; do
    echo "  Frappe not ready yet, waiting 2 seconds..."
    sleep 2
done
echo "✓ Frappe is ready"

# Load environment variables from .env file
if [ -f /opt/openclaw/assistant/.env ]; then
    export $(cat /opt/openclaw/assistant/.env | grep -v '^#' | xargs)
    echo "✓ Environment loaded"
fi

# Load Frappe credentials if separate file exists
if [ -f /opt/openclaw/frappe.env ]; then
    export $(cat /opt/openclaw/frappe.env | grep -v '^#' | xargs)
    echo "✓ Frappe credentials loaded"
fi

# Initialize openclaw if not already configured
if [ ! -f ~/.openclaw/openclaw.json ]; then
    echo "Configuring openclaw..."

    # Create openclaw config directory
    mkdir -p ~/.openclaw

    # Create openclaw configuration
    cat > ~/.openclaw/openclaw.json <<EOF
{
  "provider": "anthropic",
  "api_key_source": "environment",
  "confirmation_required": {
    "terminal": true,
    "frappe_api": true,
    "file_operations": true
  },
  "docker_sandbox": {
    "enabled": true,
    "mount_path": "/opt/openclaw/assistant",
    "restrict_access": true
  },
  "heartbeat": {
    "enabled": true,
    "interval_minutes": 5,
    "schedule": "*/5 * * * *"
  },
  "context_files": [
    "/opt/openclaw/assistant/CONTEXT.md",
    "/opt/openclaw/assistant/SKILL.md",
    "/opt/openclaw/assistant/CONVERSATIONS.md",
    "/opt/openclaw/assistant/MEMORY.md",
    "/opt/openclaw/assistant/HEARTBEAT.md"
  ],
  "ignore_file": "/opt/openclaw/assistant/.clawdignore"
}
EOF
    echo "✓ OpenClaw configured"
fi

# Set working directory to assistant
cd /opt/openclaw/assistant

# Run openclaw command (default: chat)
echo "🚀 Starting OpenClaw Assistant..."
exec openclaw "$@"
