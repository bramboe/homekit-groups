"""Virtual binary_sensor platform for 'doorbell' and 'programmable_switch'."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base import ArchitectBase
from .const import SLOT_BATTERY, SLOT_CAMERA, SLOT_TRIGGER

HANDLED_TEMPLATES = ("doorbell", "programmable_switch")

DEVICE_CLASS_MAP = {
    "doorbell": BinarySensorDeviceClass.OCCUPANCY,
    "programmable_switch": BinarySensorDeviceClass.POWER,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    tid = entry.data.get("template_id")
    if tid not in HANDLED_TEMPLATES:
        return
    slots = entry.data.get("slots") or {}
    if not slots.get(SLOT_TRIGGER):
        return
    async_add_entities([ArchitectBinarySensor(hass, entry, tid)])


class ArchitectBinarySensor(ArchitectBase, BinarySensorEntity):

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, tid: str) -> None:
        self._architect_init(hass, entry, "binary_sensor")
        self._attr_device_class = DEVICE_CLASS_MAP.get(tid)

    @callback
    def _update_state(self) -> None:
        src = self._slot(SLOT_TRIGGER)
        st = self.hass.states.get(src) if src else None
        if st and st.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self._attr_is_on = st.state == STATE_ON
        else:
            self._attr_is_on = None

        attrs = self._read_battery()
        cam = self._slot(SLOT_CAMERA)
        if cam:
            attrs["camera_entity"] = cam
        self._attr_extra_state_attributes = attrs

    async def async_added_to_hass(self) -> None:
        self._update_state()
        await self._async_track_slots(SLOT_TRIGGER, SLOT_CAMERA, SLOT_BATTERY)
