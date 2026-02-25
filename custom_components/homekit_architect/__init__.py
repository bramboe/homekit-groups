"""HomeKit Entity Architect: Virtual Accessory Builder with automated ghosting."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_AUTOMATED_GHOSTING,
    CONF_HOMEKIT_BRIDGE_ENTRY_ID,
    DOMAIN,
    TEMPLATES,
)
from .ghosting import async_apply_ghosting, get_slot_entity_ids, async_reload_homekit_bridge

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.LOCK, Platform.COVER]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration (YAML not used)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HomeKit Entity Architect from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Forward setup to the correct platform (lock or cover)
    template_type = entry.data.get("template_type")
    template = TEMPLATES.get(template_type) if template_type else None
    platform = template.get("platform") if template else "lock"
    platform_list = [Platform(platform)] if platform in ("lock", "cover") else [Platform.LOCK]

    await hass.config_entries.async_forward_entry_setups(entry, platform_list)

    # Apply ghosting: exclude slot entities from the selected HomeKit Bridge
    if entry.data.get(CONF_AUTOMATED_GHOSTING):
        if async_apply_ghosting(hass, entry):
            bridge_entry_id = entry.data.get(CONF_HOMEKIT_BRIDGE_ENTRY_ID)
            if bridge_entry_id:
                await async_reload_homekit_bridge(hass, bridge_entry_id)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and optionally remove ghosting."""
    from .ghosting import async_remove_ghosting

    # Remove slot entities from bridge exclude list so they reappear
    if entry.data.get(CONF_AUTOMATED_GHOSTING):
        async_remove_ghosting(hass, entry)
        bridge_entry_id = entry.data.get(CONF_HOMEKIT_BRIDGE_ENTRY_ID)
        if bridge_entry_id:
            await async_reload_homekit_bridge(hass, bridge_entry_id)

    template_type = entry.data.get("template_type")
    template = TEMPLATES.get(template_type) if template_type else None
    platform = template.get("platform") if template else "lock"
    platform_list = [Platform(platform)] if platform in ("lock", "cover") else [Platform.LOCK]

    unload_ok = await hass.config_entries.async_unload_platforms(entry, platform_list)
    if unload_ok and DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an Architect entry: unghost slot entities."""
    from .ghosting import async_remove_ghosting

    if entry.data.get(CONF_AUTOMATED_GHOSTING):
        async_remove_ghosting(hass, entry)
        bridge_entry_id = entry.data.get(CONF_HOMEKIT_BRIDGE_ENTRY_ID)
        if bridge_entry_id:
            await async_reload_homekit_bridge(hass, bridge_entry_id)
