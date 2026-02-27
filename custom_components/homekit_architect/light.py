"""Virtual light platform for the 'lightbulb' template.

Template pattern: state is derived from the slot entity; commands are forwarded
using the slot entity's domain. Any source type can back a virtual light:
- light: full state (on/off, brightness, color) and light.turn_on/turn_off
- fan: on/off + brightness from fan percentage; turn_on with percentage
- switch/input_boolean: on/off only
"""

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
        src = self._slot(SLOT_SWITCH)
        dom = domain_of(src) if src else ""
        if self._slot(SLOT_COLOR) and dom == "light":
            modes.add(ColorMode.HS)
        if self._slot(SLOT_BRIGHTNESS) or dom in ("light", "fan"):
            modes.add(ColorMode.BRIGHTNESS)
        if not modes:
            modes.add(ColorMode.ONOFF)
        self._attr_supported_color_modes = modes
        self._attr_color_mode = next(iter(modes))

    @callback
    def _update_state(self) -> None:
        src = self._slot(SLOT_SWITCH)
        st = self.hass.states.get(src) if src else None
        dom = domain_of(src) if src else ""
        if st and st.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self._attr_is_on = st.state == STATE_ON
            if dom == "light":
                attrs = st.attributes or {}
                if ATTR_BRIGHTNESS in attrs:
                    self._attr_brightness = attrs[ATTR_BRIGHTNESS]
                if ATTR_HS_COLOR in attrs:
                    self._attr_hs_color = attrs[ATTR_HS_COLOR]
            elif dom == "fan":
                pct = (st.attributes or {}).get("percentage")
                if pct is not None:
                    self._attr_brightness = round((pct / 100.0) * 255) if pct else 0
                elif self._attr_is_on:
                    self._attr_brightness = 255
                else:
                    self._attr_brightness = 0
            elif dom in ("switch", "input_boolean"):
                self._attr_brightness = None  # on/off only
        else:
            self._attr_is_on = None
            self._attr_brightness = None
        self._attr_extra_state_attributes = {}

    async def async_added_to_hass(self) -> None:
        self._update_state()
        await self._async_track_slots(SLOT_SWITCH, SLOT_BRIGHTNESS, SLOT_COLOR)

    async def async_turn_on(self, **kwargs: Any) -> None:
        eid = self._slot(SLOT_SWITCH)
        dom = domain_of(eid) if eid else ""
        data: dict[str, Any] = {}
        if dom == "light":
            if ATTR_BRIGHTNESS in kwargs:
                data[ATTR_BRIGHTNESS] = kwargs[ATTR_BRIGHTNESS]
            if ATTR_HS_COLOR in kwargs:
                data[ATTR_HS_COLOR] = kwargs[ATTR_HS_COLOR]
        elif dom == "fan" and (ATTR_BRIGHTNESS in kwargs or kwargs):
            brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
            data["percentage"] = min(100, max(0, round((brightness / 255.0) * 100)))
        await self._forward_service(eid, "turn_on", data if data else None)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._forward_service(self._slot(SLOT_SWITCH), "turn_off")
