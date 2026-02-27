"""Virtual cover platform for garage_door, door, window, window_covering."""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import CoverEntity, CoverDeviceClass, CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_CLOSED, STATE_CLOSING, STATE_OFF, STATE_ON,
    STATE_OPEN, STATE_OPENING, STATE_UNAVAILABLE, STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base import ArchitectBase, domain_of
from .const import (
    SLOT_ACTUATOR, SLOT_BATTERY, SLOT_OBSTRUCTION,
    SLOT_POSITION, SLOT_POSITION_SENSOR, SLOT_TILT, TEMPLATES,
)

HANDLED_TEMPLATES = ("garage_door", "door", "window", "window_covering")

DEVICE_CLASS_MAP = {
    "garage_door": CoverDeviceClass.GARAGE,
    "door": CoverDeviceClass.DOOR,
    "window": CoverDeviceClass.WINDOW,
    "window_covering": CoverDeviceClass.SHADE,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    tid = entry.data.get("template_id")
    if tid not in HANDLED_TEMPLATES:
        return
    async_add_entities([ArchitectCover(hass, entry, tid)])


class ArchitectCover(ArchitectBase, CoverEntity):

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, tid: str) -> None:
        self._architect_init(hass, entry, "cover")
        self._tid = tid
        self._attr_device_class = DEVICE_CLASS_MAP.get(tid)

        features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE
        if tid == "window_covering" and self._slot(SLOT_TILT):
            features |= CoverEntityFeature.OPEN_TILT | CoverEntityFeature.CLOSE_TILT
        self._attr_supported_features = features

    @callback
    def _update_state(self) -> None:
        if self._tid == "window_covering":
            src = self._slot(SLOT_POSITION)
        else:
            src = self._slot(SLOT_POSITION_SENSOR) or self._slot(SLOT_ACTUATOR)

        st = self.hass.states.get(src) if src else None
        val = st.state if st else STATE_UNKNOWN

        if val in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self._attr_is_closed = None
        elif val in (STATE_CLOSED, STATE_OFF):
            self._attr_is_closed = True
        elif val in (STATE_OPEN, STATE_ON):
            self._attr_is_closed = False
        elif val == STATE_OPENING:
            self._attr_is_closed = False
            self._attr_is_opening = True
        elif val == STATE_CLOSING:
            self._attr_is_closed = None
            self._attr_is_closing = True
        else:
            self._attr_is_closed = val == STATE_ON

        obs_id = self._slot(SLOT_OBSTRUCTION)
        if obs_id:
            obs = self.hass.states.get(obs_id)
            self._attr_extra_state_attributes = {"obstruction": obs and obs.state == STATE_ON}
        else:
            self._attr_extra_state_attributes = {}
        self._attr_extra_state_attributes.update(self._read_battery())

    async def async_added_to_hass(self) -> None:
        self._update_state()
        await self._async_track_slots(
            SLOT_ACTUATOR, SLOT_POSITION_SENSOR, SLOT_POSITION,
            SLOT_OBSTRUCTION, SLOT_BATTERY,
        )

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self._actuate("open")

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self._actuate("close")

    async def _actuate(self, action: str) -> None:
        eid = self._slot(SLOT_ACTUATOR) or self._slot(SLOT_POSITION)
        if not eid:
            return
        dom = domain_of(eid)
        if dom == "cover":
            await self._forward_service(eid, f"{action}_cover")
        else:
            svc = "turn_on" if action == "open" else "turn_off"
            await self._forward_service(eid, svc)
