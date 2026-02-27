"""Virtual light platform for the 'lightbulb' template."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base import ArchitectBase, domain_of
from .const import SLOT_BRIGHTNESS, SLOT_COLOR, SLOT_SWITCH

HANDLED_TEMPLATES = ("lightbulb",)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    tid = entry.data.get("template_id")
    if tid not in HANDLED_TEMPLATES:
        return
    slots = entry.data.get("slots") or {}
    if not slots.get(SLOT_SWITCH):
        return
    async_add_entities([ArchitectLight(hass, entry)])


class ArchitectLight(ArchitectBase, LightEntity):

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._architect_init(hass, entry, "light")
        modes: set[ColorMode] = set()
        if self._slot(SLOT_COLOR):
            modes.add(ColorMode.HS)
        elif self._slot(SLOT_BRIGHTNESS):
            modes.add(ColorMode.BRIGHTNESS)
        else:
            modes.add(ColorMode.ONOFF)
        self._attr_supported_color_modes = modes
        self._attr_color_mode = next(iter(modes))

    @callback
    def _update_state(self) -> None:
        src = self._slot(SLOT_SWITCH)
        st = self.hass.states.get(src) if src else None
        if st and st.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self._attr_is_on = st.state == STATE_ON
            if ATTR_BRIGHTNESS in (st.attributes or {}):
                self._attr_brightness = st.attributes[ATTR_BRIGHTNESS]
            if ATTR_HS_COLOR in (st.attributes or {}):
                self._attr_hs_color = st.attributes[ATTR_HS_COLOR]
        else:
            self._attr_is_on = None
        self._attr_extra_state_attributes = {}

    async def async_added_to_hass(self) -> None:
        self._update_state()
        await self._async_track_slots(SLOT_SWITCH, SLOT_BRIGHTNESS, SLOT_COLOR)

    async def async_turn_on(self, **kwargs: Any) -> None:
        eid = self._slot(SLOT_SWITCH)
        dom = domain_of(eid)
        data: dict[str, Any] = {}
        if ATTR_BRIGHTNESS in kwargs and dom == "light":
            data[ATTR_BRIGHTNESS] = kwargs[ATTR_BRIGHTNESS]
        if ATTR_HS_COLOR in kwargs and dom == "light":
            data[ATTR_HS_COLOR] = kwargs[ATTR_HS_COLOR]
        await self._forward_service(eid, "turn_on", data or None)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._forward_service(self._slot(SLOT_SWITCH), "turn_off")
