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

exec python3 /server.py
