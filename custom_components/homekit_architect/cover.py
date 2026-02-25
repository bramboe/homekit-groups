"""Virtual cover platform for Garage Door package: state from slots, commands to actuator."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import (
    CoverEntity,
    CoverEntityFeature,
    CoverState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_CLOSED, STATE_CLOSING, STATE_OPEN, STATE_OPENING, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_FRIENDLY_NAME,
    CONF_SLOTS,
    DOMAIN,
    SLOT_ACTUATOR,
    SLOT_BATTERY,
    SLOT_OBSTRUCTION,
    SLOT_SENSOR_OPENING,
    TEMPLATE_GARAGE_DOOR,
)

_LOGGER = logging.getLogger(__name__)

# Binary/state values that mean "open"
OPEN_VALUES = {"on", "open", "opening", "opened"}
CLOSED_VALUES = {"off", "closed", "closing", "closed"}


def _sensor_to_cover_state(state: str | None) -> CoverState | None:
    """Map slot sensor state to CoverState."""
    if state is None or state == STATE_UNKNOWN:
        return None
    s = (state or "").strip().lower()
    if s in OPEN_VALUES or s == "opening":
        return CoverState.OPEN if s != "opening" else CoverState.OPENING
    if s in CLOSED_VALUES or s == "closing":
        return CoverState.CLOSED if s != "closing" else CoverState.CLOSING
    if s == "opening":
        return CoverState.OPENING
    if s == "closing":
        return CoverState.CLOSING
    return CoverState.CLOSED if s in ("closed", "off") else CoverState.OPEN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the virtual garage door cover from a config entry."""
    if entry.data.get("template_type") != TEMPLATE_GARAGE_DOOR:
        return
    slots = entry.data.get(CONF_SLOTS) or {}
    if not slots.get(SLOT_ACTUATOR) or not slots.get(SLOT_SENSOR_OPENING):
        return
    async_add_entities([ArchitectGarageDoorEntity(hass, entry)])


class ArchitectGarageDoorEntity(CoverEntity):
    """Virtual garage door cover: state from opening sensor, commands to actuator."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_supported_features = (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
    )

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry
        self._slots = entry.data.get(CONF_SLOTS) or {}
        self._actuator_entity = self._slots.get(SLOT_ACTUATOR)
        self._sensor_entity = self._slots.get(SLOT_SENSOR_OPENING)
        self._battery_entity = self._slots.get(SLOT_BATTERY)
        self._obstruction_entity = self._slots.get(SLOT_OBSTRUCTION)

        self._attr_name = entry.data.get(CONF_FRIENDLY_NAME) or "Garage Door"
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_cover"
        self._attr_available = False
        self._attr_current_cover_position = None
        self._attr_is_closed = None
        self._attr_is_closing = False
        self._attr_is_opening = False

    @property
    def device_info(self) -> dict[str, Any] | None:
        """Return device info for the config entry."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._attr_name,
            "manufacturer": "HomeKit Architect",
            "model": "Garage Door Package",
            "entry_type": "service",
        }

    async def async_added_to_hass(self) -> None:
        """Subscribe to slot entity state changes."""
        await super().async_added_to_hass()
        entities = [
            e
            for e in (
                self._actuator_entity,
                self._sensor_entity,
                self._battery_entity,
                self._obstruction_entity,
            )
            if e
        ]
        self.async_on_remove(
            async_track_state_change_event(self.hass, entities, self._async_slot_changed)
        )
        self._async_update_from_slots()

    @callback
    def _async_slot_changed(self, event) -> None:
        """Handle state change of any slot entity."""
        self._async_update_from_slots()

    @callback
    def _async_update_from_slots(self) -> None:
        """Compute cover state from slot entities."""
        available = False
        is_closed = None
        is_opening = False
        is_closing = False

        sensor = self._sensor_entity
        if sensor:
            state = self.hass.states.get(sensor)
            if state and state.state not in (STATE_UNKNOWN, ""):
                available = True
                cov = _sensor_to_cover_state(state.state)
                if cov == CoverState.CLOSED:
                    is_closed = True
                elif cov == CoverState.OPEN:
                    is_closed = False
                elif cov == CoverState.OPENING:
                    is_opening = True
                elif cov == CoverState.CLOSING:
                    is_closing = True

        actuator = self._actuator_entity
        if actuator and is_closed is None:
            state = self.hass.states.get(actuator)
            if state and state.state not in (STATE_UNKNOWN, ""):
                available = True
                cov = _sensor_to_cover_state(state.state)
                if cov == CoverState.CLOSED:
                    is_closed = True
                elif cov == CoverState.OPEN:
                    is_closed = False

        self._attr_available = available
        self._attr_is_closed = is_closed
        self._attr_is_opening = is_opening
        self._attr_is_closing = is_closing
        self.async_write_ha_state()

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open: forward to actuator (switch on or cover open)."""
        if not self._actuator_entity:
            return
        domain = self._actuator_entity.split(".", 1)[0]
        if domain == "switch":
            await self.hass.services.async_call(
                "switch", "turn_on", {"entity_id": self._actuator_entity}, blocking=True
            )
        elif domain == "cover":
            await self.hass.services.async_call(
                "cover", "open_cover", {"entity_id": self._actuator_entity}, blocking=True
            )
        else:
            _LOGGER.warning("Unsupported actuator domain: %s", domain)
        self._async_update_from_slots()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close: forward to actuator (switch off or cover close)."""
        if not self._actuator_entity:
            return
        domain = self._actuator_entity.split(".", 1)[0]
        if domain == "switch":
            await self.hass.services.async_call(
                "switch", "turn_off", {"entity_id": self._actuator_entity}, blocking=True
            )
        elif domain == "cover":
            await self.hass.services.async_call(
                "cover", "close_cover", {"entity_id": self._actuator_entity}, blocking=True
            )
        else:
            _LOGGER.warning("Unsupported actuator domain: %s", domain)
        self._async_update_from_slots()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop: forward to cover actuator if it's a cover."""
        if not self._actuator_entity:
            return
        domain = self._actuator_entity.split(".", 1)[0]
        if domain == "cover":
            await self.hass.services.async_call(
                "cover", "stop_cover", {"entity_id": self._actuator_entity}, blocking=True
            )
        self._async_update_from_slots()
