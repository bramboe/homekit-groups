"""Virtual switch platform for switch, outlet, faucet, shower, sprinkler.

Template pattern: state from slot entity (any domain with on/off); commands
forwarded using the slot's domain (light.turn_on, fan.turn_on, switch.turn_on, etc.).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base import ArchitectBase, domain_of
from .const import SLOT_BATTERY, SLOT_POWER_SENSOR, SLOT_STATE, SLOT_SWITCH, SLOT_TIMER

HANDLED_TEMPLATES = ("switch", "outlet", "faucet", "shower", "sprinkler", "multi_service")

DEVICE_CLASS_MAP = {
    "outlet": SwitchDeviceClass.OUTLET,
    "switch": SwitchDeviceClass.SWITCH,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    tid = entry.data.get("template_id")
    if tid not in HANDLED_TEMPLATES:
        return
    slots = entry.data.get("slots") or {}
    if tid == "multi_service":
        switch_slots = [k for k, eid in slots.items() if eid and domain_of(eid) == "switch"]
        if not switch_slots:
            return
        async_add_entities([ArchitectSwitch(hass, entry, tid, slot_key=sk) for sk in switch_slots])
        return
    if not slots.get(SLOT_SWITCH):
        return
    async_add_entities([ArchitectSwitch(hass, entry, tid)])


class ArchitectSwitch(ArchitectBase, SwitchEntity):

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        tid: str,
        slot_key: str | None = None,
    ) -> None:
        self._architect_init(hass, entry, "switch", slot_key=slot_key)
        self._switch_slot_key = slot_key if slot_key else SLOT_SWITCH
        dc = DEVICE_CLASS_MAP.get(tid)
        if dc:
            self._attr_device_class = dc

    @callback
    def _update_state(self) -> None:
        state_eid = self._slot(SLOT_STATE) or self._slot(self._switch_slot_key)
        st = self.hass.states.get(state_eid) if state_eid else None
        if st and st.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self._attr_is_on = st.state == STATE_ON
        else:
            self._attr_is_on = None

        attrs = self._read_battery()
        pwr = self._slot(SLOT_POWER_SENSOR)
        if pwr:
            pst = self.hass.states.get(pwr)
            if pst and pst.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                try:
                    attrs["power_w"] = float(pst.state)
                except (TypeError, ValueError):
                    pass
        self._attr_extra_state_attributes = attrs

    async def async_added_to_hass(self) -> None:
        self._update_state()
        await self._async_track_slots(
            self._switch_slot_key, SLOT_STATE, SLOT_POWER_SENSOR, SLOT_BATTERY, SLOT_TIMER
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        eid = self._slot(self._switch_slot_key)
        await self._forward_service(eid, "turn_on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        eid = self._slot(self._switch_slot_key)
        await self._forward_service(eid, "turn_off")
