"""Virtual fan platform for 'fan' and 'air_purifier' templates."""

from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
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
        if self._slot(SLOT_SPEED):
            features |= FanEntityFeature.SET_SPEED
        self._attr_supported_features = features

    @callback
    def _update_state(self) -> None:
        src = self._slot(self._switch_slot_key)
        st = self.hass.states.get(src) if src else None
        if st and st.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self._attr_is_on = st.state == STATE_ON
            if "percentage" in (st.attributes or {}):
                self._attr_percentage = st.attributes["percentage"]
        else:
            self._attr_is_on = None

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

    async def async_turn_on(self, percentage: int | None = None, **kwargs: Any) -> None:
        eid = self._slot(self._switch_slot_key)
        data: dict[str, Any] = {}
        if percentage is not None and domain_of(eid) == "fan":
            data["percentage"] = percentage
        await self._forward_service(eid, "turn_on", data or None)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._forward_service(self._slot(self._switch_slot_key), "turn_off")

    async def async_set_percentage(self, percentage: int) -> None:
        eid = self._slot(SLOT_SPEED) or self._slot(self._switch_slot_key)
        dom = domain_of(eid)
        if dom == "fan":
            await self._forward_service(eid, "set_percentage", {"percentage": percentage})
        elif dom in ("number", "input_number"):
            await self._forward_service(eid, "set_value", {"value": percentage})
