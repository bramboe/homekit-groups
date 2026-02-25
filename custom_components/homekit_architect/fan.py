"""Virtual Fan platform for HomeKit Entity Architect."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_APPLY_GHOST_HIDE,
    CONF_BRIDGE_ID,
    CONF_ENTITY_NAME,
    CONF_MEMBER_ENTITIES,
    FAN_SLOT_BATTERY,
    FAN_SLOT_SPEED,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the virtual fan from a config entry."""
    async_add_entities([ArchitectFanEntity(config_entry)])


def _normalize_percentage(state: str, attrs: dict) -> int:
    """Map light/fan/switch state to 0-100 percentage."""
    if state == STATE_OFF:
        return 0
    if state == STATE_ON:
        brightness = attrs.get("brightness")
        if brightness is not None:
            return round((brightness / 255) * 100)
        percentage = attrs.get("percentage")
        if percentage is not None:
            return percentage
        return 100
    return 0


class ArchitectFanEntity(FanEntity):
    """A virtual fan that mirrors a light, fan, or switch for HomeKit."""

    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_supported_features = FanEntityFeature.SET_SPEED | FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the architect fan."""
        self._config_entry = config_entry
        self._speed_entity_id: str | None = config_entry.data.get(CONF_MEMBER_ENTITIES, {}).get(
            FAN_SLOT_SPEED
        )
        self._battery_entity_id: str | None = config_entry.data.get(CONF_MEMBER_ENTITIES, {}).get(
            FAN_SLOT_BATTERY
        ) or None
        if not self._battery_entity_id:
            self._battery_entity_id = None

        name = config_entry.data.get(CONF_ENTITY_NAME) or "Architect Fan"
        self._attr_name = name
        self._attr_unique_id = f"{config_entry.entry_id}_fan"
        self._attr_percentage = 0
        self._attr_available = True

    @callback
    def _recover_state(self) -> None:
        """Recover state from source entities (state preservation after restart)."""
        if not self._speed_entity_id:
            return
        state = self.hass.states.get(self._speed_entity_id)
        if state:
            self._attr_percentage = _normalize_percentage(state.state, state.attributes)
            self._attr_available = state.state not in ("unavailable", "unknown")
        else:
            self._attr_available = False

    async def async_added_to_hass(self) -> None:
        """Run when entity is added: recover state and apply Ghost if enabled."""
        self._recover_state()

        # Track source entity changes
        if self._speed_entity_id:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [self._speed_entity_id],
                    self._handle_speed_change,
                )
            )

        # Ghost method: update HomeKit bridge to exclude sources and include this entity
        if (
            self._config_entry.data.get(CONF_APPLY_GHOST_HIDE)
            and self._config_entry.data.get(CONF_BRIDGE_ID)
        ):
            from homekit_architect import async_update_homekit_bridge

            bridge_id = self._config_entry.data[CONF_BRIDGE_ID]
            members = self._config_entry.data.get(CONF_MEMBER_ENTITIES) or {}
            to_exclude = [e for e in members.values() if e]
            to_include = [self.entity_id]
            await async_update_homekit_bridge(self.hass, bridge_id, to_exclude, to_include)

    @callback
    def _handle_speed_change(self, event) -> None:
        """Update our state when the source entity changes."""
        state = self.hass.states.get(self._speed_entity_id)
        if state:
            self._attr_percentage = _normalize_percentage(state.state, state.attributes)
            self._attr_available = state.state not in ("unavailable", "unknown")
        self.async_write_ha_state()

    @property
    def percentage(self) -> int | None:
        """Return current percentage."""
        return self._attr_percentage

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan or set percentage."""
        if not self._speed_entity_id:
            return
        if percentage is not None:
            await self.async_set_percentage(percentage)
            return
        await self.hass.services.async_call(
            "homeassistant",
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: self._speed_entity_id},
            blocking=True,
        )
        self._recover_state()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        if not self._speed_entity_id:
            return
        await self.hass.services.async_call(
            "homeassistant",
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: self._speed_entity_id},
            blocking=True,
        )
        self._attr_percentage = 0
        self.async_write_ha_state()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set fan speed percentage (maps to light brightness or fan percentage)."""
        if not self._speed_entity_id:
            return
        state = self.hass.states.get(self._speed_entity_id)
        if not state:
            return
        domain = state.domain
        if domain == "light":
            brightness = round((percentage / 100) * 255)
            await self.hass.services.async_call(
                "light",
                "turn_on",
                {ATTR_ENTITY_ID: self._speed_entity_id, "brightness": brightness},
                blocking=True,
            )
        elif domain == "fan":
            await self.hass.services.async_call(
                "fan",
                "set_percentage",
                {ATTR_ENTITY_ID: self._speed_entity_id, "percentage": percentage},
                blocking=True,
            )
        else:
            if percentage > 0:
                await self.hass.services.async_call(
                    "homeassistant",
                    SERVICE_TURN_ON,
                    {ATTR_ENTITY_ID: self._speed_entity_id},
                    blocking=True,
                )
            else:
                await self.hass.services.async_call(
                    "homeassistant",
                    SERVICE_TURN_OFF,
                    {ATTR_ENTITY_ID: self._speed_entity_id},
                    blocking=True,
                )
        self._attr_percentage = percentage
        self.async_write_ha_state()
