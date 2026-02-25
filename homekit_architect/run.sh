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
SOURCE="/data/integration/homekit_architect"

if [ ! -d "${SOURCE}" ]; then
  echo "[HomeKit Entity Architect] ERROR: Integration not found at ${SOURCE}. Rebuild the add-on image." >&2
  exit 1
fi

mkdir -p "${CONFIG}/custom_components"
rm -rf "${TARGET}"
cp -r "${SOURCE}" "${TARGET}"

echo "[HomeKit Entity Architect] Integration installed to ${TARGET}"
echo "[HomeKit Entity Architect] Restart Home Assistant to load the integration."
echo "[HomeKit Entity Architect] Use the 'Open Web UI' button above to open the configuration screen."

# Run ingress redirect server so "Open Web UI" sends users to the configuration panel
exec python3 /ingress_redirect.py
