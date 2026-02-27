"""HomeKit Bridge ghosting: exclude slot entities, include virtual architect entity."""

from __future__ import annotations

import asyncio
import logging
from copy import deepcopy

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_EXCLUDE_ENTITIES,
    CONF_FILTER,
    CONF_HOMEKIT_BRIDGE_ENTRY_ID,
    CONF_INCLUDE_ENTITIES,
    CONF_SLOTS,
    DOMAIN,
    OPTION_GHOSTING_VIRTUAL_ENTITY_ID,
    OPTION_GHOSTING_VIRTUAL_ENTITY_IDS,
    TEMPLATES,
)
from . import get_all_virtual_entity_ids


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

    virtual_entity_ids: list[str] = []
    for _ in range(6):
        virtual_entity_ids = get_all_virtual_entity_ids(hass, entry)
        if virtual_entity_ids:
            break
        await asyncio.sleep(1.0)
    if not virtual_entity_ids:
        _LOGGER.warning(
            "HomeKit Architect: no virtual entities found for entry %s; slot entities will be hidden but grouped entity may not appear in Home until HA is restarted",
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

    if virtual_entity_ids:
        include = list(filt.get(CONF_INCLUDE_ENTITIES) or [])
        for eid in virtual_entity_ids:
            if eid not in include:
                include.append(eid)
        filt[CONF_INCLUDE_ENTITIES] = sorted(set(include))
        # Store for remove cleanup when entity is gone (e.g. on integration remove)
        arch_opts = dict(entry.options or {})
        arch_opts[OPTION_GHOSTING_VIRTUAL_ENTITY_ID] = virtual_entity_ids[0]
        arch_opts[OPTION_GHOSTING_VIRTUAL_ENTITY_IDS] = virtual_entity_ids
        hass.config_entries.async_update_entry(entry, options=arch_opts)

    options[CONF_FILTER] = filt
    hass.config_entries.async_update_entry(homekit_entry, options=options)
    # Delay reload so the bridge can release its port before restarting (avoids Errno 98)
    await asyncio.sleep(5.0)
    await hass.config_entries.async_reload(homekit_entry.entry_id)
    _LOGGER.info(
        "HomeKit Architect: applied ghosting for entry %s on bridge %s",
        entry.title,
        homekit_entry.title,
    )


def _filter_entity_ids_belonging_to_entry(
    entity_ids: list[str], entry: ConfigEntry
) -> list[str]:
    """Return entity_ids that belong to this Architect entry (for cleanup when entity is gone)."""
    eid = entry.entry_id
    return [x for x in entity_ids if eid in x]


async def async_remove_ghosting(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """
    Remove this Architect entry's slot entities and virtual entity from the
    bridge filter (so they revert to bridge default behavior) and reload.
    Uses stored virtual_entity_id when present so cleanup works even after
    the entity is removed (e.g. when integration/add-on is removed with "remove data").
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

    opts = entry.options or {}
    virtual_entity_ids: set[str] = set()
    stored_ids = opts.get(OPTION_GHOSTING_VIRTUAL_ENTITY_IDS)
    if isinstance(stored_ids, list):
        virtual_entity_ids.update(stored_ids)
    elif opts.get(OPTION_GHOSTING_VIRTUAL_ENTITY_ID):
        virtual_entity_ids.add(opts[OPTION_GHOSTING_VIRTUAL_ENTITY_ID])
    if not virtual_entity_ids:
        virtual_entity_ids.update(get_all_virtual_entity_ids(hass, entry))
    slot_entity_ids = get_slot_entity_ids(entry)
    to_remove = set(slot_entity_ids) | virtual_entity_ids

    options = deepcopy(dict(homekit_entry.options))
    filt = options.get(CONF_FILTER) or {}
    filt = dict(filt)

    # Also remove any filter entity that belongs to this entry (e.g. virtual entity id
    # that we couldn't resolve because the entity was already removed)
    all_in_filter = list(filt.get(CONF_EXCLUDE_ENTITIES) or []) + list(
        filt.get(CONF_INCLUDE_ENTITIES) or []
    )
    for eid in _filter_entity_ids_belonging_to_entry(all_in_filter, entry):
        to_remove.add(eid)

    exclude = [e for e in (filt.get(CONF_EXCLUDE_ENTITIES) or []) if e not in to_remove]
    filt[CONF_EXCLUDE_ENTITIES] = exclude

    include = [e for e in (filt.get(CONF_INCLUDE_ENTITIES) or []) if e not in to_remove]
    filt[CONF_INCLUDE_ENTITIES] = include

    options[CONF_FILTER] = filt
    hass.config_entries.async_update_entry(homekit_entry, options=options)

    # Clear stored virtual entity ids from our entry
    keys_to_remove = (OPTION_GHOSTING_VIRTUAL_ENTITY_ID, OPTION_GHOSTING_VIRTUAL_ENTITY_IDS)
    arch_opts = {k: v for k, v in (entry.options or {}).items() if k not in keys_to_remove}
    if arch_opts != dict(entry.options or {}):
        hass.config_entries.async_update_entry(entry, options=arch_opts)

    await asyncio.sleep(5.0)
    await hass.config_entries.async_reload(homekit_entry.entry_id)
    _LOGGER.info(
        "HomeKit Architect: removed ghosting for entry %s from bridge %s",
        entry.title,
        homekit_entry.title,
    )


