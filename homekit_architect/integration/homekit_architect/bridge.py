"""HomeKit Bridge ghosting: exclude slot entities, include virtual architect entity."""

from __future__ import annotations

import logging
from copy import deepcopy

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_FILTER,
    CONF_HOMEKIT_BRIDGE_ENTRY_ID,
    CONF_EXCLUDE_ENTITIES,
    CONF_INCLUDE_ENTITIES,
    CONF_SLOTS,
    DOMAIN,
    TEMPLATES,
)


def get_slot_entity_ids(entry: ConfigEntry) -> list[str]:
    """Return list of entity_ids assigned to slots for this entry."""
    slots: dict = entry.data.get(CONF_SLOTS) or {}
    return [e for e in slots.values() if e]


_LOGGER = logging.getLogger(__name__)

HOMEKIT_DOMAIN = "homekit"


async def async_apply_ghosting(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """
    Update the selected HomeKit Bridge so that:
    - All slot entity_ids for this Architect entry are excluded.
    - The virtual Architect entity is included.
    Then reload the HomeKit bridge so Apple Home reflects changes.
    """
    bridge_entry_id = entry.data.get(CONF_HOMEKIT_BRIDGE_ENTRY_ID)
    if not bridge_entry_id:
        return

    homekit_entry = hass.config_entries.async_get_entry(bridge_entry_id)
    if not homekit_entry or homekit_entry.domain != HOMEKIT_DOMAIN:
        _LOGGER.warning(
            "HomeKit Architect: bridge entry_id %s not found or not HomeKit",
            bridge_entry_id,
        )
        return

    template_id = entry.data.get("template_id")
    template = TEMPLATES.get(template_id) if template_id else None
    if not template:
        return

    platform = template["platform"]
    virtual_entity_id = _get_virtual_entity_id(hass, entry, platform)
    if not virtual_entity_id:
        _LOGGER.debug(
            "HomeKit Architect: virtual %s entity not yet registered for entry %s",
            platform,
            entry.entry_id,
        )
    slot_entity_ids = get_slot_entity_ids(entry)

    options = deepcopy(dict(homekit_entry.options))
    filt = options.get(CONF_FILTER) or {}
    filt = dict(filt)

    exclude = list(filt.get(CONF_EXCLUDE_ENTITIES) or [])
    for e in slot_entity_ids:
        if e and e not in exclude:
            exclude.append(e)
    filt[CONF_EXCLUDE_ENTITIES] = sorted(set(exclude))

    if virtual_entity_id:
        include = list(filt.get(CONF_INCLUDE_ENTITIES) or [])
        if virtual_entity_id not in include:
            include.append(virtual_entity_id)
        filt[CONF_INCLUDE_ENTITIES] = sorted(set(include))

    options[CONF_FILTER] = filt
    hass.config_entries.async_update_entry(homekit_entry, options=options)
    await hass.config_entries.async_reload(homekit_entry.entry_id)
    _LOGGER.info(
        "HomeKit Architect: applied ghosting for entry %s on bridge %s",
        entry.title,
        homekit_entry.title,
    )


async def async_remove_ghosting(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """
    Remove this Architect entry's slot entities and virtual entity from the
    bridge filter (so they revert to bridge default behavior) and reload.
    """
    bridge_entry_id = entry.data.get(CONF_HOMEKIT_BRIDGE_ENTRY_ID)
    if not bridge_entry_id:
        return

    homekit_entry = hass.config_entries.async_get_entry(bridge_entry_id)
    if not homekit_entry or homekit_entry.domain != HOMEKIT_DOMAIN:
        return

    template_id = entry.data.get("template_id")
    template = TEMPLATES.get(template_id) if template_id else None
    if not template:
        return

    platform = template["platform"]
    virtual_entity_id = _get_virtual_entity_id(hass, entry, platform)
    slot_entity_ids = get_slot_entity_ids(entry)
    to_remove = set(slot_entity_ids) | ({virtual_entity_id} if virtual_entity_id else set())

    options = deepcopy(dict(homekit_entry.options))
    filt = options.get(CONF_FILTER) or {}
    filt = dict(filt)

    exclude = [e for e in (filt.get(CONF_EXCLUDE_ENTITIES) or []) if e not in to_remove]
    filt[CONF_EXCLUDE_ENTITIES] = exclude

    include = [e for e in (filt.get(CONF_INCLUDE_ENTITIES) or []) if e not in to_remove]
    filt[CONF_INCLUDE_ENTITIES] = include

    options[CONF_FILTER] = filt
    hass.config_entries.async_update_entry(homekit_entry, options=options)
    await hass.config_entries.async_reload(homekit_entry.entry_id)
    _LOGGER.info(
        "HomeKit Architect: removed ghosting for entry %s from bridge %s",
        entry.title,
        homekit_entry.title,
    )


def _get_virtual_entity_id(hass: HomeAssistant, entry: ConfigEntry, platform: str) -> str | None:
    """Resolve virtual entity_id from entity registry."""
    reg = er.async_get(hass)
    unique_id = f"{DOMAIN}_{entry.entry_id}_{platform}"
    return reg.async_get_entity_id(platform, DOMAIN, unique_id)
