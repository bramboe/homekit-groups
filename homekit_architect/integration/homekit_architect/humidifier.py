"""Virtual humidifier platform for 'humidifier' and 'dehumidifier' templates."""

from __future__ import annotations

from typing import Any

from homeassistant.components.humidifier import HumidifierEntity, HumidifierDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base import ArchitectBase, domain_of
from .const import SLOT_HUMIDITY_SENSOR, SLOT_SWITCH, SLOT_TARGET

HANDLED_TEMPLATES = ("humidifier", "dehumidifier")


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    tid = entry.data.get("template_id")
    if tid not in HANDLED_TEMPLATES:
        return
    slots = entry.data.get("slots") or {}
    if not slots.get(SLOT_SWITCH):
        return
    async_add_entities([ArchitectHumidifier(hass, entry, tid)])


class ArchitectHumidifier(ArchitectBase, HumidifierEntity):

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, tid: str) -> None:
        self._architect_init(hass, entry, "humidifier")
        self._attr_device_class = (
            HumidifierDeviceClass.HUMIDIFIER if tid == "humidifier"
            else HumidifierDeviceClass.DEHUMIDIFIER
        )

    @callback
    def _update_state(self) -> None:
        src = self._slot(SLOT_SWITCH)
        st = self.hass.states.get(src) if src else None
        if st and st.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self._attr_is_on = st.state == STATE_ON
            if "current_humidity" in (st.attributes or {}):
                self._attr_current_humidity = st.attributes["current_humidity"]
            if "humidity" in (st.attributes or {}):
                self._attr_target_humidity = st.attributes["humidity"]
        else:
            self._attr_is_on = None

        hum_id = self._slot(SLOT_HUMIDITY_SENSOR)
        if hum_id and not getattr(self, "_attr_current_humidity", None):
            hs = self.hass.states.get(hum_id)
            if hs and hs.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                try:
                    self._attr_current_humidity = float(hs.state)
                except (TypeError, ValueError):
                    pass
        self._attr_extra_state_attributes = {}

    async def async_added_to_hass(self) -> None:
        self._update_state()
        await self._async_track_slots(SLOT_SWITCH, SLOT_HUMIDITY_SENSOR, SLOT_TARGET)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._forward_service(self._slot(SLOT_SWITCH), "turn_on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._forward_service(self._slot(SLOT_SWITCH), "turn_off")

    async def async_set_humidity(self, humidity: int) -> None:
        eid = self._slot(SLOT_TARGET) or self._slot(SLOT_SWITCH)
        dom = domain_of(eid)
        if dom == "humidifier":
            await self._forward_service(eid, "set_humidity", {"humidity": humidity})
        elif dom in ("number", "input_number"):
            await self._forward_service(eid, "set_value", {"value": humidity})
