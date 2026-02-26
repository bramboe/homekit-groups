#!/bin/sh
set -e

# Home Assistant config directory (mounted via map: homeassistant_config:rw)
# Try common mount paths used by Supervisor
if [ -d /config ] && [ -w /config ]; then
  CONFIG="/config"
elif [ -d /homeassistant ] && [ -w /homeassistant ]; then
  CONFIG="/homeassistant"
else
  CONFIG="${CONFIG:-/config}"
fi

TARGET="${CONFIG}/custom_components/homekit_architect"
SOURCE="/usr/share/homekit_architect/homekit_architect"

# Respect add-on option reinstall_on_start (from Configuration tab)
REINSTALL_ON_START="true"
if [ -f /data/options.json ]; then
  REINSTALL_ON_START=$(python3 -c "
import json
try:
    o = json.load(open('/data/options.json'))
    print(str(o.get('reinstall_on_start', True)).lower())
except Exception:
    print('true')
" 2>/dev/null || echo "true")
fi

mkdir -p "${CONFIG}/custom_components"
if [ "$REINSTALL_ON_START" = "true" ]; then
  rm -rf "${TARGET}"
  cp -r "${SOURCE}" "${TARGET}"
  echo "[HomeKit Entity Architect] Integration installed to ${TARGET}"
  echo "[HomeKit Entity Architect] Restart Home Assistant to load the integration."
else
  echo "[HomeKit Entity Architect] Skipping install (reinstall_on_start is false). Use Web UI to reinstall."
fi
echo "[HomeKit Entity Architect] Open the add-on Web UI for configuration."

# Run config server for ingress (keeps container running)
exec python3 /server.py
