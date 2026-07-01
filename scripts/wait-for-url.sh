#!/usr/bin/env bash
# Wait for a URL to return HTTP 200 (or any 2xx) within a timeout.
# Usage: ./scripts/wait-for-url.sh <url> <timeout_seconds>
set -euo pipefail

URL="${1:?Usage: wait-for-url.sh <url> <timeout_seconds>}"
TIMEOUT="${2:-120}"
ELAPSED=0

echo "Waiting for ${URL} (timeout: ${TIMEOUT}s)..."

while [ "$ELAPSED" -lt "$TIMEOUT" ]; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL" 2>/dev/null || echo "000")
  if [ "$STATUS" -ge 200 ] && [ "$STATUS" -lt 300 ]; then
    echo "✅ ${URL} is ready (HTTP ${STATUS}) after ${ELAPSED}s"
    exit 0
  fi
  sleep 2
  ELAPSED=$((ELAPSED + 2))
done

echo "❌ ${URL} did not become ready within ${TIMEOUT}s (last status: ${STATUS})"
exit 1
