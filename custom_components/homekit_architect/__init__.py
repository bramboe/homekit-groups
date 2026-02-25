"""HomeKit Entity Architect: group entities into a single HomeKit-compatible accessory."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_APPLY_GHOST_HIDE, CONF_BRIDGE_ID, CONF_MEMBER_ENTITIES, DOMAIN, HOMEKIT_DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_update_homekit_bridge(
    hass: HomeAssistant,
    bridge_id: str,
    to_exclude: list[str],
    to_include: list[str],
) -> None:
    """
    Update the HomeKit Bridge filter: exclude source entities, include the new virtual entity.
    (The "Ghost" method.)
    """
    entry = hass.config_entries.async_get_entry(bridge_id)
    if not entry or entry.domain != HOMEKIT_DOMAIN:
        _LOGGER.warning("HomeKit bridge entry %s not found or invalid", bridge_id)
        return

    new_options = dict(entry.options)
    new_options.setdefault("exclude_entities", [])
    new_options.setdefault("include_entities", [])

    exclude = list(set(new_options["exclude_entities"]) | set(to_exclude))
    include = list(set(new_options["include_entities"]) | set(to_include))
    new_options["exclude_entities"] = exclude
    new_options["include_entities"] = include

    hass.config_entries.async_update_entry(entry, options=new_options)
    await hass.config_entries.async_reload(bridge_id)
    _LOGGER.info(
        "Updated HomeKit bridge %s: excluded %s, included %s",
        bridge_id,
        to_exclude,
        to_include,
    )


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration (no YAML config)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HomeKit Entity Architect from a config entry."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Forward to platform(s) based on target domain
    target = entry.data.get("target_domain", "fan")
    platforms = [Platform.FAN] if target == "fan" else [Platform.FAN]
    await hass.config_entries.async_forward_entry_setups(entry, platforms)

    # Ghost method is applied from the fan platform in async_added_to_hass once entity_id is known.

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    target = entry.data.get("target_domain", "fan")
    platforms = [Platform.FAN] if target == "fan" else [Platform.FAN]
    unload_ok = await hass.config_entries.async_unload_forward_entry_setups(entry, platforms)
    if unload_ok and DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
