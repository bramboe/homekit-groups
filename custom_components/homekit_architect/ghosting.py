"""HomeKit Bridge ghosting: exclude slot entities and optionally reload the bridge."""

from __future__ import annotations

import logging
from copy import deepcopy

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entityfilter import (
    CONF_EXCLUDE_ENTITIES,
)

from .const import (
    CONF_FILTER,
    CONF_HOMEKIT_BRIDGE_ENTRY_ID,
    CONF_SLOTS,
    HOMEKIT_DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def get_slot_entity_ids(entry: ConfigEntry) -> set[str]:
    """Return the set of entity_ids assigned to slots for this Architect entry."""
    slots = entry.data.get(CONF_SLOTS) or {}
    return {eid for eid in slots.values() if eid}


@callback
def async_apply_ghosting(
    hass: HomeAssistant,
    architect_entry: ConfigEntry,
    slot_entity_ids: set[str] | None = None,
) -> bool:
    """
    Update the target HomeKit Bridge's filter to exclude the given slot entity_ids.
    Does not reload the bridge; caller should reload if needed.
    Returns True if the bridge options were updated.
    """
    bridge_entry_id = architect_entry.data.get(CONF_HOMEKIT_BRIDGE_ENTRY_ID)
    if not bridge_entry_id:
        return False
    bridge_entry = hass.config_entries.async_get_entry(bridge_entry_id)
    if not bridge_entry or bridge_entry.domain != HOMEKIT_DOMAIN:
        _LOGGER.warning("HomeKit Bridge config entry %s not found", bridge_entry_id)
        return False

    if slot_entity_ids is None:
        slot_entity_ids = get_slot_entity_ids(architect_entry)
    if not slot_entity_ids:
        return False

    options = deepcopy(dict(bridge_entry.options))
    filter_config = options.get(CONF_FILTER) or {}
    filter_config = deepcopy(filter_config)
    exclude = list(filter_config.get(CONF_EXCLUDE_ENTITIES) or [])
    exclude_set = set(exclude) | slot_entity_ids
    filter_config[CONF_EXCLUDE_ENTITIES] = sorted(exclude_set)
    options[CONF_FILTER] = filter_config

    hass.config_entries.async_update_entry(bridge_entry, options=options)
    _LOGGER.debug(
        "Updated HomeKit Bridge %s exclude_entities: %s",
        bridge_entry_id,
        filter_config[CONF_EXCLUDE_ENTITIES],
    )
    return True


@callback
def async_remove_ghosting(
    hass: HomeAssistant,
    architect_entry: ConfigEntry,
    slot_entity_ids: set[str] | None = None,
) -> bool:
    """
    Remove the given slot entity_ids from the target HomeKit Bridge's exclude list.
    Returns True if the bridge options were updated.
    """
    bridge_entry_id = architect_entry.data.get(CONF_HOMEKIT_BRIDGE_ENTRY_ID)
    if not bridge_entry_id:
        return False
    bridge_entry = hass.config_entries.async_get_entry(bridge_entry_id)
    if not bridge_entry or bridge_entry.domain != HOMEKIT_DOMAIN:
        return False

    if slot_entity_ids is None:
        slot_entity_ids = get_slot_entity_ids(architect_entry)
    if not slot_entity_ids:
        return False

    options = deepcopy(dict(bridge_entry.options))
    filter_config = options.get(CONF_FILTER) or {}
    filter_config = deepcopy(filter_config)
    exclude = list(filter_config.get(CONF_EXCLUDE_ENTITIES) or [])
    exclude_set = set(exclude) - slot_entity_ids
    filter_config[CONF_EXCLUDE_ENTITIES] = sorted(exclude_set)
    options[CONF_FILTER] = filter_config

    hass.config_entries.async_update_entry(bridge_entry, options=options)
    _LOGGER.debug(
        "Removed from HomeKit Bridge %s exclude_entities: %s",
        bridge_entry_id,
        filter_config[CONF_EXCLUDE_ENTITIES],
    )
    return True


async def async_reload_homekit_bridge(
    hass: HomeAssistant, bridge_entry_id: str
) -> None:
    """Reload the HomeKit Bridge config entry so it picks up filter changes."""
    await hass.config_entries.async_reload(bridge_entry_id)
    _LOGGER.debug("Reloaded HomeKit Bridge %s", bridge_entry_id)
