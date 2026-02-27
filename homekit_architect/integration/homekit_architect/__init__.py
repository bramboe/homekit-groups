"""HomeKit Entity Architect – Virtual Accessory Builder for Home Assistant."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_AUTOMATED_GHOSTING,
    CONF_HOMEKIT_BRIDGE_ENTRY_ID,
    CONF_SLOTS,
    DOMAIN,
    MULTI_SERVICE_DOMAIN_TO_PLATFORM,
    TEMPLATES,
)
from .base import domain_of
from .bridge import async_apply_ghosting, async_remove_ghosting
from .websocket_api import async_register_websocket_handlers

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the HomeKit Entity Architect integration (WebSocket API only).

    The UI is served exclusively by the add-on via ingress now, so we no
    longer register a separate sidebar panel from the integration itself.
    """
    async_register_websocket_handlers(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a single Architect config entry and load its platform."""
    template_id = entry.data.get("template_id")
    if not template_id:
        return False

    template = TEMPLATES.get(template_id)
    if not template:
        return False

    if template_id == "multi_service":
        slots = entry.data.get(CONF_SLOTS) or {}
        slot_domains = {domain_of(eid) for eid in slots.values() if eid}
        platforms = sorted(
            {MULTI_SERVICE_DOMAIN_TO_PLATFORM[d] for d in slot_domains if d in MULTI_SERVICE_DOMAIN_TO_PLATFORM}
        )
        if not platforms:
            return False
    else:
        platforms = template.get("platforms") or [template["platform"]]
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "entry": entry,
        "template_id": template_id,
        "template": template,
    }

    await hass.config_entries.async_forward_entry_setups(entry, platforms)

    if entry.data.get(CONF_AUTOMATED_GHOSTING) and entry.data.get(
        CONF_HOMEKIT_BRIDGE_ENTRY_ID
    ):
        # Let the entity registry pick up the new virtual entity before applying ghosting
        await asyncio.sleep(2.0)
        await async_apply_ghosting(hass, entry)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle config entry options/update (e.g. ghosting toggle or bridge change)."""
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

    if template_id == "multi_service":
        slots = entry.data.get(CONF_SLOTS) or {}
        slot_domains = {domain_of(eid) for eid in slots.values() if eid}
        platforms = sorted(
            {MULTI_SERVICE_DOMAIN_TO_PLATFORM[d] for d in slot_domains if d in MULTI_SERVICE_DOMAIN_TO_PLATFORM}
        )
    else:
        platforms = template.get("platforms") or [template["platform"]]
    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok


def get_virtual_entity_id(
    hass: HomeAssistant,
    entry: ConfigEntry,
    platform: str,
    slot_key: str | None = None,
) -> str | None:
    """Resolve the virtual entity's entity_id from the entity registry."""
    reg = er.async_get(hass)
    if slot_key:
        unique_id = f"{DOMAIN}_{entry.entry_id}_{platform}_{slot_key}"
    else:
        unique_id = f"{DOMAIN}_{entry.entry_id}_{platform}"
    return reg.async_get_entity_id(platform, DOMAIN, unique_id)


def get_all_virtual_entity_ids(hass: HomeAssistant, entry: ConfigEntry) -> list[str]:
    """Return all virtual entity_ids for this Architect entry (for bridge ghosting)."""
    template_id = entry.data.get("template_id")
    template = TEMPLATES.get(template_id) if template_id else None
    if not template:
        return []
    platforms = template.get("platforms") or [template.get("platform")]
    if not platforms:
        return []
    slots = entry.data.get(CONF_SLOTS) or {}
    result: list[str] = []
    if template_id == "multi_service":
        for slot_key, eid in slots.items():
            if not eid:
                continue
            domain = domain_of(eid)
            platform = MULTI_SERVICE_DOMAIN_TO_PLATFORM.get(domain)
            if not platform:
                continue
            eid_resolved = get_virtual_entity_id(hass, entry, platform, slot_key)
            if eid_resolved and eid_resolved not in result:
                result.append(eid_resolved)
    else:
        for platform in platforms:
            eid_resolved = get_virtual_entity_id(hass, entry, platform, None)
            if eid_resolved:
                result.append(eid_resolved)
    return result
