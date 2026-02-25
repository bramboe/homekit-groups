"""HomeKit Entity Architect – Virtual Accessory Builder for Home Assistant."""

from __future__ import annotations

import logging
import os
from typing import Any

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_AUTOMATED_GHOSTING,
    CONF_HOMEKIT_BRIDGE_ENTRY_ID,
    DOMAIN,
    TEMPLATES,
)
from .bridge import async_apply_ghosting, async_remove_ghosting
from .websocket_api import async_register_websocket_handlers

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the HomeKit Entity Architect integration (panel + WebSocket API)."""
    async_register_websocket_handlers(hass)

    frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
    if os.path.isdir(frontend_path):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(f"/{DOMAIN}_panel", frontend_path, False)]
        )
        await frontend.async_register_built_in_panel(
            hass,
            component_name="custom",
            sidebar_title="HomeKit Architect",
            sidebar_icon="mdi:apple-homekit",
            frontend_url_path="homekit-architect",
            config={
                "_panel_custom": {
                    "name": "homekit-architect-panel",
                    "js_url": f"/{DOMAIN}_panel/homekit-architect.js",
                },
            },
            require_admin=True,
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a single Architect config entry and load its platform."""
    template_id = entry.data.get("template_id")
    if not template_id:
        return False

    template = TEMPLATES.get(template_id)
    if not template:
        return False

    platform = template["platform"]
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "entry": entry,
        "template_id": template_id,
        "template": template,
    }

    await hass.config_entries.async_forward_entry_setups(entry, [platform])

    if entry.data.get(CONF_AUTOMATED_GHOSTING) and entry.data.get(
        CONF_HOMEKIT_BRIDGE_ENTRY_ID
    ):
        await async_apply_ghosting(hass, entry)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle config entry options/update."""
    if entry.data.get(CONF_AUTOMATED_GHOSTING) and entry.data.get(
        CONF_HOMEKIT_BRIDGE_ENTRY_ID
    ):
        await async_apply_ghosting(hass, entry)
    else:
        await async_remove_ghosting(hass, entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an Architect entry and remove ghosting from the bridge."""
    await async_remove_ghosting(hass, entry)

    template_id = entry.data.get("template_id")
    if not template_id:
        return True

    template = TEMPLATES.get(template_id)
    if not template:
        return True

    platform = template["platform"]
    unload_ok = await hass.config_entries.async_unload_platforms(entry, [platform])
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok


def get_virtual_entity_id(hass: HomeAssistant, entry: ConfigEntry, platform: str) -> str | None:
    """Resolve the virtual entity's entity_id from the entity registry."""
    reg = er.async_get(hass)
    unique_id = f"{DOMAIN}_{entry.entry_id}_{platform}"
    return reg.async_get_entity_id(platform, DOMAIN, unique_id)
