"""Virtual sensor platform for the 'sensor' template."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base import ArchitectBase
from .const import SLOT_BATTERY, SLOT_PRIMARY, SLOT_SECONDARY

HANDLED_TEMPLATES = ("sensor",)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    tid = entry.data.get("template_id")
    if tid not in HANDLED_TEMPLATES:
        return
    slots = entry.data.get("slots") or {}
    if not slots.get(SLOT_PRIMARY):
        return
    async_add_entities([ArchitectSensor(hass, entry)])


class ArchitectSensor(ArchitectBase, SensorEntity):

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._architect_init(hass, entry, "sensor")

    @callback
    def _update_state(self) -> None:
        src = self._slot(SLOT_PRIMARY)
        st = self.hass.states.get(src) if src else None
        if st and st.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self._attr_native_value = st.state
            self._attr_native_unit_of_measurement = (st.attributes or {}).get("unit_of_measurement")
            dc = (st.attributes or {}).get("device_class")
            if dc:
                self._attr_device_class = dc
        else:
            self._attr_native_value = None

        attrs = self._read_battery()
        sec = self._slot(SLOT_SECONDARY)
        if sec:
            ss = self.hass.states.get(sec)
            if ss and ss.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                attrs["secondary"] = ss.state
        self._attr_extra_state_attributes = attrs

    async def async_added_to_hass(self) -> None:
        self._update_state()
        await self._async_track_slots(SLOT_PRIMARY, SLOT_SECONDARY, SLOT_BATTERY)
