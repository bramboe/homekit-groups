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
from .const import SLOT_BRIGHTNESS, SLOT_COLOR, SLOT_SWITCH, TEMPLATES

HANDLED_TEMPLATES = ("lightbulb", "fan_light", "multi_service")


def _light_switch_slot_key(template_id: str) -> str:
    """Slot key for light on/off (combo template uses light_switch_slot)."""
    t = TEMPLATES.get(template_id) or {}
    return t.get("platform_slots", {}).get("light") or SLOT_SWITCH


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    tid = entry.data.get("template_id")
    if tid not in HANDLED_TEMPLATES:
        return
    slots = entry.data.get("slots") or {}
    if tid == "multi_service":
        light_slots = [k for k, eid in slots.items() if eid and domain_of(eid) == "light"]
        if not light_slots:
            return
        async_add_entities([ArchitectLight(hass, entry, slot_key=sk) for sk in light_slots])
        return
    switch_key = _light_switch_slot_key(tid)
    if not slots.get(switch_key):
        return
    async_add_entities([ArchitectLight(hass, entry)])


class ArchitectLight(ArchitectBase, LightEntity):

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        slot_key: str | None = None,
    ) -> None:
        self._architect_init(hass, entry, "light", slot_key=slot_key)
        tid = entry.data.get("template_id", "")
        self._switch_slot_key = slot_key if slot_key else _light_switch_slot_key(tid)
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
        src = self._slot(self._switch_slot_key)
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
        await self._async_track_slots(
            self._switch_slot_key, SLOT_BRIGHTNESS, SLOT_COLOR
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        eid = self._slot(self._switch_slot_key)
        dom = domain_of(eid)
        data: dict[str, Any] = {}
        if ATTR_BRIGHTNESS in kwargs and dom == "light":
            data[ATTR_BRIGHTNESS] = kwargs[ATTR_BRIGHTNESS]
        if ATTR_HS_COLOR in kwargs and dom == "light":
            data[ATTR_HS_COLOR] = kwargs[ATTR_HS_COLOR]
        await self._forward_service(eid, "turn_on", data or None)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._forward_service(self._slot(self._switch_slot_key), "turn_off")
