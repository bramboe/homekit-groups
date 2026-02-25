"""Virtual lock platform: state from state_slot, commands to action_slot."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.lock import LockEntity, LockState
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_ARCHITECT_ENTITY_FRIENDLY_NAME,
    CONF_SLOTS,
    DOMAIN,
    SLOT_ACTION,
    SLOT_BATTERY,
    SLOT_OBSTRUCTION,
    SLOT_STATE,
    TEMPLATE_SECURITY_LOCK,
    TEMPLATES,
)

_LOGGER = logging.getLogger(__name__)

# State slot: door contact "on" typically means closed = locked
STATE_SLOT_ON_MEANS_LOCKED = True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual lock from a config entry."""
    if entry.data.get("template_id") != TEMPLATE_SECURITY_LOCK:
        return
    template = TEMPLATES[TEMPLATE_SECURITY_LOCK]
    slots = entry.data.get(CONF_SLOTS) or {}
    if not slots.get(SLOT_ACTION) or not slots.get(SLOT_STATE):
        return

    entity = ArchitectLockEntity(hass, entry, template, slots)
    async_add_entities([entity])


class ArchitectLockEntity(LockEntity):
    """Single virtual lock combining action, state, optional battery and obstruction."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        template: dict,
        slots: dict[str, str],
    ) -> None:
        self.hass = hass
        self._entry = entry
        self._template = template
        self._slots = slots
        self._action_entity = slots.get(SLOT_ACTION) or ""
        self._state_entity = slots.get(SLOT_STATE) or ""
        self._battery_entity = slots.get(SLOT_BATTERY) or ""
        self._obstruction_entity = slots.get(SLOT_OBSTRUCTION) or ""

        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_lock"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.data.get(CONF_ARCHITECT_ENTITY_FRIENDLY_NAME) or template["name"],
            "manufacturer": "HomeKit Architect",
            "model": template["name"],
        }
        friendly = entry.data.get(CONF_ARCHITECT_ENTITY_FRIENDLY_NAME) or template["name"]
        self._attr_translation_key = "architect_lock"
        # Fallback name if no translation
        self._attr_name = friendly

    @callback
    def _state_slot_to_lock_state(self, state: str, state_attr: dict) -> LockState:
        """Map state slot (e.g. door contact) to LockState."""
        if state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return LockState.UNKNOWN
        # Door contact: on = closed → locked, off = open → unlocked
        if STATE_SLOT_ON_MEANS_LOCKED:
            return LockState.LOCKED if state == STATE_ON else LockState.UNLOCKED
        return LockState.UNLOCKED if state == STATE_ON else LockState.LOCKED

    @callback
    def _update_state(self) -> None:
        """Update lock state from state slot and optional battery/obstruction."""
        state_state = self.hass.states.get(self._state_entity)
        state_val = state_state.state if state_state else STATE_UNKNOWN
        self._attr_is_locked = (
            self._state_slot_to_lock_state(
                state_val,
                state_state.attributes if state_state else {},
            )
            == LockState.LOCKED
        )

        # Jammed from obstruction slot
        obs_state = self.hass.states.get(self._obstruction_entity) if self._obstruction_entity else None
        self._attr_is_jammed = (
            obs_state is not None and obs_state.state == STATE_ON
        )

        # Battery from optional battery slot
        self._attr_extra_state_attributes = {}
        if self._battery_entity:
            bat_state = self.hass.states.get(self._battery_entity)
            if bat_state is not None and bat_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                try:
                    level = int(float(bat_state.state))
                    self._attr_extra_state_attributes[ATTR_BATTERY_LEVEL] = level
                except (TypeError, ValueError):
                    pass

    async def async_added_to_hass(self) -> None:
        """Subscribe to slot entities."""
        self._update_state()

        @callback
        def _on_slot_change(event):
            self._update_state()
            self.async_write_ha_state()

        entities = [
            e
            for e in [
                self._state_entity,
                self._obstruction_entity,
                self._battery_entity,
            ]
            if e
        ]
        self.async_on_remove(
            async_track_state_change_event(self.hass, entities, _on_slot_change)
        )

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock: forward to action slot."""
        await self.hass.services.async_call(
            _domain_for_entity(self._action_entity),
            "lock" if _domain_for_entity(self._action_entity) == "lock" else "turn_on",
            {"entity_id": self._action_entity},
            blocking=True,
        )

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock: forward to action slot."""
        await self.hass.services.async_call(
            _domain_for_entity(self._action_entity),
            "unlock" if _domain_for_entity(self._action_entity) == "lock" else "turn_off",
            {"entity_id": self._action_entity},
            blocking=True,
        )


def _domain_for_entity(entity_id: str) -> str:
    return entity_id.split(".", 1)[0] if "." in entity_id else "switch"
