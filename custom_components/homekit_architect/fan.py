"""Virtual fan platform for 'fan' and 'air_purifier' templates.

Supports any entity type as the source (like a template fan): e.g. a light
can drive the fan (state = on/off, percentage from brightness, commands
forwarded to light.turn_on with brightness_pct). Works for fan, light, switch.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.components.light import ATTR_BRIGHTNESS
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base import ArchitectBase, domain_of
from .const import (
    SLOT_AIR_QUALITY,
    SLOT_BATTERY,
    SLOT_FILTER,
    SLOT_SPEED,
    SLOT_SWITCH,
    TEMPLATES,
)

HANDLED_TEMPLATES = ("fan", "air_purifier", "fan_light", "multi_service")

# Map fan percentage to light brightness_pct (3 speeds: Low 25%, Medium 50%, High 75%)
FAN_PCT_TO_BRIGHTNESS = (25, 50, 75)
PRESET_MODES = ("Low", "Medium", "High")


def _brightness_to_fan_percentage(brightness: int | None) -> int:
    """Map light brightness (0-255) to fan percentage (33, 66, 100). Off -> 33 (Low)."""
    if brightness is None or brightness <= 0:
        return 33
    pct = round((brightness / 2.55))
    if pct <= 25:
        return 33
    if pct <= 50:
        return 66
    return 100


def _fan_percentage_to_brightness_pct(percentage: int) -> int:
    """Map fan percentage to light brightness_pct (25, 50, 75)."""
    if percentage <= 33:
        return 25
    if percentage <= 66:
        return 50
    return 75


def _fan_switch_slot_key(template_id: str) -> str:
    """Slot key for fan on/off (combo template uses fan_switch_slot)."""
    t = TEMPLATES.get(template_id) or {}
    return t.get("platform_slots", {}).get("fan") or SLOT_SWITCH


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    tid = entry.data.get("template_id")
    if tid not in HANDLED_TEMPLATES:
        return
    slots = entry.data.get("slots") or {}
    if tid == "multi_service":
        fan_slots = [k for k, eid in slots.items() if eid and domain_of(eid) == "fan"]
        if not fan_slots:
            return
        async_add_entities([ArchitectFan(hass, entry, slot_key=sk) for sk in fan_slots])
        return
    switch_key = _fan_switch_slot_key(tid)
    if not slots.get(switch_key):
        return
    async_add_entities([ArchitectFan(hass, entry)])


class ArchitectFan(ArchitectBase, FanEntity):

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        slot_key: str | None = None,
    ) -> None:
        self._architect_init(hass, entry, "fan", slot_key=slot_key)
        tid = entry.data.get("template_id", "")
        self._switch_slot_key = slot_key if slot_key else _fan_switch_slot_key(tid)
        features = FanEntityFeature(0)
        switch_id = self._slot(self._switch_slot_key)
        dom = domain_of(switch_id) if switch_id else ""
        if self._slot(SLOT_SPEED) or dom == "fan":
            features |= FanEntityFeature.SET_SPEED
        if dom == "light":
            features |= FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE
        if dom in ("switch", "input_boolean"):
            features |= FanEntityFeature.SET_SPEED  # on=100%, off=0%
        self._attr_supported_features = features
        self._attr_preset_modes = list(PRESET_MODES) if dom == "light" else None
        self._attr_speed_count = 3 if dom == "light" else 100

    @callback
    def _update_state(self) -> None:
        src = self._slot(self._switch_slot_key)
        st = self.hass.states.get(src) if src else None
        dom = domain_of(src) if src else ""
        if st and st.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self._attr_is_on = st.state == STATE_ON
            if dom == "light":
                brightness = (st.attributes or {}).get(ATTR_BRIGHTNESS)
                self._attr_percentage = _brightness_to_fan_percentage(brightness)
                pct = self._attr_percentage
                self._attr_preset_mode = (
                    PRESET_MODES[0] if pct <= 33 else PRESET_MODES[1] if pct <= 66 else PRESET_MODES[2]
                )
            elif "percentage" in (st.attributes or {}):
                self._attr_percentage = st.attributes["percentage"]
            elif self._attr_is_on:
                self._attr_percentage = 100
            else:
                self._attr_percentage = None
        else:
            self._attr_is_on = None
            self._attr_percentage = None
            if dom == "light":
                self._attr_preset_mode = PRESET_MODES[0]

        attrs = self._read_battery()
        aq = self._slot(SLOT_AIR_QUALITY)
        if aq:
            aqst = self.hass.states.get(aq)
            if aqst and aqst.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                attrs["air_quality"] = aqst.state
        fl = self._slot(SLOT_FILTER)
        if fl:
            flst = self.hass.states.get(fl)
            if flst and flst.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                attrs["filter_life"] = flst.state
        self._attr_extra_state_attributes = attrs

    async def async_added_to_hass(self) -> None:
        self._update_state()
        await self._async_track_slots(
            self._switch_slot_key, SLOT_SPEED, SLOT_AIR_QUALITY, SLOT_FILTER, SLOT_BATTERY
        )

    def _switch_domain(self) -> str:
        eid = self._slot(self._switch_slot_key)
        return domain_of(eid) if eid else ""

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        eid = self._slot(self._switch_slot_key)
        dom = self._switch_domain()
        if dom == "light":
            # Like template: turn_on -> light at default/low (25%) if no percentage
            brightness_pct = 25
            if percentage is not None:
                brightness_pct = _fan_percentage_to_brightness_pct(percentage)
            elif preset_mode in PRESET_MODES:
                idx = PRESET_MODES.index(preset_mode)
                brightness_pct = FAN_PCT_TO_BRIGHTNESS[idx]
            await self.hass.services.async_call(
                "light", "turn_on", {"entity_id": eid, "brightness_pct": brightness_pct}, blocking=True
            )
            return
        data: dict[str, Any] = {}
        if percentage is not None and dom == "fan":
            data["percentage"] = percentage
        await self._forward_service(eid, "turn_on", data or None)

    async def async_turn_off(self, **kwargs: Any) -> None:
        eid = self._slot(self._switch_slot_key)
        dom = self._switch_domain()
        if dom == "light":
            # Template style: turn_off -> Low speed (25% brightness)
            await self.hass.services.async_call(
                "light", "turn_on", {"entity_id": eid, "brightness_pct": 25}, blocking=True
            )
            return
        await self._forward_service(eid, "turn_off")

    async def async_set_percentage(self, percentage: int) -> None:
        eid = self._slot(SLOT_SPEED) or self._slot(self._switch_slot_key)
        dom = domain_of(eid) if eid else ""
        if dom == "light":
            await self.hass.services.async_call(
                "light",
                "turn_on",
                {"entity_id": eid, "brightness_pct": _fan_percentage_to_brightness_pct(percentage)},
                blocking=True,
            )
            return
        if dom in ("switch", "input_boolean"):
            await self._forward_service(eid, "turn_on" if percentage > 0 else "turn_off")
            return
        if dom == "fan":
            await self._forward_service(eid, "set_percentage", {"percentage": percentage})
        elif dom in ("number", "input_number"):
            await self._forward_service(eid, "set_value", {"value": percentage})

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        eid = self._slot(self._switch_slot_key)
        if domain_of(eid) != "light" or preset_mode not in PRESET_MODES:
            return
        idx = PRESET_MODES.index(preset_mode)
        brightness_pct = FAN_PCT_TO_BRIGHTNESS[idx]
        await self.hass.services.async_call(
            "light", "turn_on", {"entity_id": eid, "brightness_pct": brightness_pct}, blocking=True
        )
