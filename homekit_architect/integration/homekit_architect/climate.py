"""Virtual climate platform for 'thermostat' template (proxies a climate entity)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base import ArchitectBase, domain_of
from .const import SLOT_CLIMATE, SLOT_HUMIDITY_SENSOR, SLOT_TEMPERATURE_SENSOR

HANDLED_TEMPLATES = ("thermostat", "multi_service")


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    tid = entry.data.get("template_id")
    if tid not in HANDLED_TEMPLATES:
        return
    slots = entry.data.get("slots") or {}
    if tid == "multi_service":
        climate_slots = [k for k, eid in slots.items() if eid and domain_of(eid) == "climate"]
        if not climate_slots:
            return
        async_add_entities([ArchitectClimate(hass, entry, slot_key=sk) for sk in climate_slots])
        return
    if not slots.get(SLOT_CLIMATE):
        return
    async_add_entities([ArchitectClimate(hass, entry)])


class ArchitectClimate(ArchitectBase, ClimateEntity):
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO]

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        slot_key: str | None = None,
    ) -> None:
        self._architect_init(hass, entry, "climate", slot_key=slot_key)
        self._climate_slot = slot_key if slot_key else SLOT_CLIMATE
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        self._attr_hvac_mode = HVACMode.OFF

    @callback
    def _update_state(self) -> None:
        src = self._slot(self._climate_slot)
        st = self.hass.states.get(src) if src else None
        if st and st.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                self._attr_hvac_mode = HVACMode(st.state)
            except ValueError:
                self._attr_hvac_mode = HVACMode.OFF
            attrs = st.attributes or {}
            self._attr_target_temperature = attrs.get("temperature")
            self._attr_current_temperature = attrs.get("current_temperature")
            self._attr_hvac_modes = attrs.get("hvac_modes", self._attr_hvac_modes)
            self._attr_min_temp = attrs.get("min_temp", 7)
            self._attr_max_temp = attrs.get("max_temp", 35)
        else:
            self._attr_hvac_mode = HVACMode.OFF

        temp_id = self._slot(SLOT_TEMPERATURE_SENSOR) if not self._multi_slot_key else None
        if temp_id and not self._attr_current_temperature:
            ts = self.hass.states.get(temp_id)
            if ts and ts.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                try:
                    self._attr_current_temperature = float(ts.state)
                except (TypeError, ValueError):
                    pass

        attrs_extra: dict[str, Any] = {}
        hum_id = self._slot(SLOT_HUMIDITY_SENSOR) if not self._multi_slot_key else None
        if hum_id:
            hs = self.hass.states.get(hum_id)
            if hs and hs.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                try:
                    attrs_extra["current_humidity"] = float(hs.state)
                except (TypeError, ValueError):
                    pass
        self._attr_extra_state_attributes = attrs_extra

    async def async_added_to_hass(self) -> None:
        self._update_state()
        await self._async_track_slots(self._climate_slot, SLOT_TEMPERATURE_SENSOR, SLOT_HUMIDITY_SENSOR)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await self._forward_service(self._slot(self._climate_slot), "set_hvac_mode", {"hvac_mode": hvac_mode})

    async def async_set_temperature(self, **kwargs: Any) -> None:
        data: dict[str, Any] = {}
        if ATTR_TEMPERATURE in kwargs:
            data[ATTR_TEMPERATURE] = kwargs[ATTR_TEMPERATURE]
        await self._forward_service(self._slot(self._climate_slot), "set_temperature", data)
