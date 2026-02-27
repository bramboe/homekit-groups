#!/bin/sh
set -e

if [ -d /homeassistant ] && [ -w /homeassistant ]; then
  CONFIG="/homeassistant"
elif [ -d /config ] && [ -w /config ]; then
  CONFIG="/config"
else
  CONFIG="${CONFIG:-/config}"
fi

TARGET="${CONFIG}/custom_components/homekit_architect"
SOURCE="/usr/share/homekit_architect/homekit_architect"

mkdir -p "${CONFIG}/custom_components"
rm -rf "${TARGET}"
cp -r "${SOURCE}" "${TARGET}"
echo "[HomeKit Architect] Integration installed to ${TARGET}"

# Ensure the integration is listed in configuration.yaml so HA loads it
YAML="${CONFIG}/configuration.yaml"
if [ -f "${YAML}" ]; then
  if ! grep -q '^homekit_architect:' "${YAML}"; then
    printf '\nhomekit_architect:\n' >> "${YAML}"
    echo "[HomeKit Architect] Added homekit_architect: to configuration.yaml"
  fi
fi

exec python3 /server.py
