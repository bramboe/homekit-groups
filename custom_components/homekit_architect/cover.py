"""Virtual cover platform for Garage Door: actuator + position sensor."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import (
    CoverEntity,
    CoverState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OFF,
    STATE_ON,
    STATE_OPEN,
    STATE_OPENING,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_ARCHITECT_ENTITY_FRIENDLY_NAME,
    CONF_SLOTS,
    DOMAIN,
    SLOT_ACTUATOR,
    SLOT_BATTERY,
    SLOT_POSITION_SENSOR,
    TEMPLATE_GARAGE_DOOR,
    TEMPLATES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual garage door cover from a config entry."""
    if entry.data.get("template_id") != TEMPLATE_GARAGE_DOOR:
        return
    template = TEMPLATES[TEMPLATE_GARAGE_DOOR]
    slots = entry.data.get(CONF_SLOTS) or {}
    if not slots.get(SLOT_ACTUATOR) or not slots.get(SLOT_POSITION_SENSOR):
        return

    entity = ArchitectCoverEntity(hass, entry, template, slots)
    async_add_entities([entity])


class ArchitectCoverEntity(CoverEntity):
    """Virtual garage door: actuator slot for commands, position sensor for state."""

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
        self._actuator_entity = slots.get(SLOT_ACTUATOR) or ""
        self._position_entity = slots.get(SLOT_POSITION_SENSOR) or ""
        self._battery_entity = slots.get(SLOT_BATTERY) or ""

        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_cover"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.data.get(CONF_ARCHITECT_ENTITY_FRIENDLY_NAME) or template["name"],
            "manufacturer": "HomeKit Architect",
            "model": template["name"],
        }
        friendly = entry.data.get(CONF_ARCHITECT_ENTITY_FRIENDLY_NAME) or template["name"]
        self._attr_name = friendly

        # Garage door in HomeKit is typically open/closed; we don't assume position support
        self._attr_supported_features = 0

    @callback
    def _position_to_cover_state(self, state: str, attrs: dict) -> CoverState:
        """Map position sensor state to CoverState."""
        if state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return CoverState.UNKNOWN
        if state == STATE_OPEN or state == "open":
            return CoverState.OPEN
        if state == STATE_CLOSED or state == "closed":
            return CoverState.CLOSED
        if state == STATE_OPENING:
            return CoverState.OPENING
        if state == STATE_CLOSING:
            return CoverState.CLOSING
        # Binary sensor: on often means closed
        if state == STATE_ON:
            return CoverState.CLOSED
        if state == STATE_OFF:
            return CoverState.OPEN
        return CoverState.UNKNOWN

    @callback
    def _update_state(self) -> None:
        """Update cover state from position sensor and optional battery."""
        pos_state = self.hass.states.get(self._position_entity)
        state_val = pos_state.state if pos_state else STATE_UNKNOWN
        attrs = pos_state.attributes if pos_state else {}
        self._attr_state = self._position_to_cover_state(state_val, attrs)

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

        entities = [e for e in [self._position_entity, self._battery_entity] if e]
        self.async_on_remove(
            async_track_state_change_event(self.hass, entities, _on_slot_change)
        )

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open garage: forward to actuator."""
        await self._call_actuator("open")

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close garage: forward to actuator."""
        await self._call_actuator("close")

    async def _call_actuator(self, action: str) -> None:
        """Call actuator entity (cover or switch)."""
        domain = _domain_for_entity(self._actuator_entity)
        if domain == "cover":
            await self.hass.services.async_call(
                "cover",
                f"{action}_cover",
                {"entity_id": self._actuator_entity},
                blocking=True,
            )
        else:
            # Switch: assume on = close, off = open (or toggle)
            await self.hass.services.async_call(
                "switch",
                "turn_on" if action == "close" else "turn_off",
                {"entity_id": self._actuator_entity},
                blocking=True,
            )


def _domain_for_entity(entity_id: str) -> str:
    return entity_id.split(".", 1)[0] if "." in entity_id else "switch"
