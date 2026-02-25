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

mkdir -p "${CONFIG}/custom_components"
rm -rf "${TARGET}"
cp -r "${SOURCE}" "${TARGET}"

echo "[HomeKit Entity Architect] Integration installed to ${TARGET}"
echo "[HomeKit Entity Architect] Restart Home Assistant to load the integration."
echo "[HomeKit Entity Architect] Then: Settings → Devices & services → Add integration → HomeKit Entity Architect."

exit 0
