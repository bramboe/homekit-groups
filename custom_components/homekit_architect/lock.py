"""Virtual lock platform: combines state from slots and routes commands to action slot."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    STATE_LOCKED,
    STATE_UNLOCKED,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_FRIENDLY_NAME,
    CONF_SLOTS,
    DEFAULT_LOW_BATTERY_THRESHOLD,
    DOMAIN,
    SLOT_ACTION,
    SLOT_BATTERY,
    SLOT_OBSTRUCTION,
    SLOT_STATE,
    TEMPLATE_SECURITY_LOCK,
)

_LOGGER = logging.getLogger(__name__)

# States that map to "locked" for state slot (contact closed = locked)
LOCKED_STATES = {STATE_LOCKED, "locked", "closed"}
# Binary sensor "on" often means closed/locked
LOCKED_BINARY_ON = {"on", "closed", "locked"}


def _state_slot_to_locked(state: str | None, domain: str) -> bool | None:
    """Convert state slot value to is_locked. Returns None if unknown."""
    if state is None or state == STATE_UNKNOWN:
        return None
    state_lower = (state or "").strip().lower()
    if domain == "binary_sensor":
        return state_lower in LOCKED_BINARY_ON
    if domain == "lock":
        return state_lower in ("locked", "locking")
    if domain == "sensor":
        return state_lower in ("locked", "closed", "locked")
    return state_lower in LOCKED_STATES


def _action_slot_supports_lock(domain: str) -> bool:
    return domain in ("lock", "switch")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the virtual lock from a config entry (Security Accessory template)."""
    if entry.data.get("template_type") != TEMPLATE_SECURITY_LOCK:
        return
    slots = entry.data.get(CONF_SLOTS) or {}
    if not slots.get(SLOT_ACTION) or not slots.get(SLOT_STATE):
        return
    async_add_entities([ArchitectLockEntity(hass, entry)])


class ArchitectLockEntity(LockEntity):
    """Virtual lock that combines state from slots and forwards commands to the action slot."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry
        self._slots = entry.data.get(CONF_SLOTS) or {}
        self._action_entity = self._slots.get(SLOT_ACTION)
        self._state_entity = self._slots.get(SLOT_STATE)
        self._battery_entity = self._slots.get(SLOT_BATTERY)
        self._obstruction_entity = self._slots.get(SLOT_OBSTRUCTION)

        self._attr_name = entry.data.get(CONF_FRIENDLY_NAME) or "Security Lock"
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_lock"
        self._attr_is_locked = None
        self._attr_is_jammed = False
        self._attr_available = False
        self._low_battery = False

    @property
    def device_info(self) -> dict[str, Any] | None:
        """Return device info linking to the config entry."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._attr_name,
            "manufacturer": "HomeKit Architect",
            "model": "Security Accessory",
            "entry_type": "service",
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose battery and slot entities for diagnostics."""
        attrs = {}
        if self._battery_entity:
            attrs["battery_entity"] = self._battery_entity
        if self._obstruction_entity:
            attrs["obstruction_entity"] = self._obstruction_entity
        if self._low_battery:
            attrs["low_battery"] = True
        return attrs

    async def async_added_to_hass(self) -> None:
        """Subscribe to slot entity state changes."""
        await super().async_added_to_hass()

        entities_to_track = [
            e
            for e in (
                self._action_entity,
                self._state_entity,
                self._battery_entity,
                self._obstruction_entity,
            )
            if e
        ]
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                entities_to_track,
                self._async_slot_changed,
            )
        )
        self._async_update_from_slots()

    @callback
    def _async_slot_changed(self, event) -> None:
        """Handle state change of any slot entity."""
        self._async_update_from_slots()

    @callback
    def _async_update_from_slots(self) -> None:
        """Compute lock state and availability from slot entities."""
        available = False
        is_locked = None
        is_jammed = False
        low_battery = False

        state_entity = self._state_entity
        if state_entity:
            state = self.hass.states.get(state_entity)
            if state and state.state not in (STATE_UNKNOWN, ""):
                available = True
                domain = state_entity.split(".", 1)[0]
                is_locked = _state_slot_to_locked(state.state, domain)

        action_entity = self._action_entity
        if action_entity and is_locked is None:
            state = self.hass.states.get(action_entity)
            if state and state.state not in (STATE_UNKNOWN, ""):
                available = True
                domain = action_entity.split(".", 1)[0]
                is_locked = _state_slot_to_locked(state.state, domain)

        if self._obstruction_entity:
            state = self.hass.states.get(self._obstruction_entity)
            if state and str(state.state).lower() in ("on", "open", "yes", "true", "jammed"):
                is_jammed = True

        if self._battery_entity:
            state = self.hass.states.get(self._battery_entity)
            if state and state.state not in (STATE_UNKNOWN, ""):
                try:
                    level = float(state.state)
                    if level < DEFAULT_LOW_BATTERY_THRESHOLD:
                        low_battery = True
                except (TypeError, ValueError):
                    pass
            if state and state.attributes.get(ATTR_BATTERY_LEVEL) is not None:
                try:
                    level = float(state.attributes[ATTR_BATTERY_LEVEL])
                    if level < DEFAULT_LOW_BATTERY_THRESHOLD:
                        low_battery = True
                except (TypeError, ValueError):
                    pass

        self._attr_available = available
        self._attr_is_locked = is_locked
        self._attr_is_jammed = is_jammed
        self._low_battery = low_battery
        self.async_write_ha_state()

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock: forward to action slot."""
        if not self._action_entity:
            return
        domain = self._action_entity.split(".", 1)[0]
        if domain == "lock":
            await self.hass.services.async_call(
                "lock",
                "lock",
                {"entity_id": self._action_entity},
                blocking=True,
            )
        elif domain == "switch":
            await self.hass.services.async_call(
                "switch",
                "turn_on",
                {"entity_id": self._action_entity},
                blocking=True,
            )
        else:
            _LOGGER.warning("Unsupported action slot domain: %s", domain)
        self._async_update_from_slots()

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock: forward to action slot."""
        if not self._action_entity:
            return
        domain = self._action_entity.split(".", 1)[0]
        if domain == "lock":
            await self.hass.services.async_call(
                "lock",
                "unlock",
                {"entity_id": self._action_entity},
                blocking=True,
            )
        elif domain == "switch":
            await self.hass.services.async_call(
                "switch",
                "turn_off",
                {"entity_id": self._action_entity},
                blocking=True,
            )
        else:
            _LOGGER.warning("Unsupported action slot domain: %s", domain)
        self._async_update_from_slots()
