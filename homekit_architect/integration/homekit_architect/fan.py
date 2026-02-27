"""Virtual fan platform for 'fan' and 'air_purifier' templates."""

from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base import ArchitectBase, domain_of
from .const import SLOT_AIR_QUALITY, SLOT_BATTERY, SLOT_FILTER, SLOT_SPEED, SLOT_SWITCH

HANDLED_TEMPLATES = ("fan", "air_purifier")


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    tid = entry.data.get("template_id")
    if tid not in HANDLED_TEMPLATES:
        return
    slots = entry.data.get("slots") or {}
    if not slots.get(SLOT_SWITCH):
        return
    async_add_entities([ArchitectFan(hass, entry)])


class ArchitectFan(ArchitectBase, FanEntity):

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._architect_init(hass, entry, "fan")
        features = FanEntityFeature(0)
        if self._slot(SLOT_SPEED):
            features |= FanEntityFeature.SET_SPEED
        self._attr_supported_features = features

    @callback
    def _update_state(self) -> None:
        src = self._slot(SLOT_SWITCH)
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
        await self._async_track_slots(SLOT_SWITCH, SLOT_SPEED, SLOT_AIR_QUALITY, SLOT_FILTER, SLOT_BATTERY)

    async def async_turn_on(self, percentage: int | None = None, **kwargs: Any) -> None:
        eid = self._slot(SLOT_SWITCH)
        data: dict[str, Any] = {}
        if percentage is not None and domain_of(eid) == "fan":
            data["percentage"] = percentage
        await self._forward_service(eid, "turn_on", data or None)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._forward_service(self._slot(SLOT_SWITCH), "turn_off")

    async def async_set_percentage(self, percentage: int) -> None:
        eid = self._slot(SLOT_SPEED) or self._slot(SLOT_SWITCH)
        dom = domain_of(eid)
        if dom == "fan":
            await self._forward_service(eid, "set_percentage", {"percentage": percentage})
        elif dom in ("number", "input_number"):
            await self._forward_service(eid, "set_value", {"value": percentage})
