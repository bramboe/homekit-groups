"""Virtual alarm_control_panel platform for 'security_system' template.

Template pattern: state from slot entity (any domain); commands by slot domain.
Alarm entity: native state. Switch/light/fan: on = armed_home, off = disarmed;
arm/disarm forward to turn_on/turn_off."""

from __future__ import annotations

from typing import Any

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base import ArchitectBase, domain_of, slot_entity_is_on
from .const import SLOT_ARM, SLOT_BATTERY, SLOT_STATE

HANDLED_TEMPLATES = ("security_system",)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    tid = entry.data.get("template_id")
    if tid not in HANDLED_TEMPLATES:
        return
    slots = entry.data.get("slots") or {}
    if not slots.get(SLOT_ARM):
        return
    async_add_entities([ArchitectAlarm(hass, entry)])


class ArchitectAlarm(ArchitectBase, AlarmControlPanelEntity):

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._architect_init(hass, entry, "alarm_control_panel")
        self._attr_supported_features = (
            AlarmControlPanelEntityFeature.ARM_HOME
            | AlarmControlPanelEntityFeature.ARM_AWAY
        )

    @callback
    def _update_state(self) -> None:
        src = self._slot(SLOT_ARM)
        st = self.hass.states.get(src) if src else None
        dom = domain_of(src) if src else ""
        if dom == "alarm_control_panel" and st and st.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                self._attr_alarm_state = AlarmControlPanelState(st.state)
            except ValueError:
                self._attr_alarm_state = AlarmControlPanelState.DISARMED
        else:
            # Any other domain (switch, light, fan): on = armed_home, off = disarmed
            is_on = slot_entity_is_on(self.hass, src) if src else None
            self._attr_alarm_state = (
                AlarmControlPanelState.ARMED_HOME if is_on else AlarmControlPanelState.DISARMED
            )
        self._attr_extra_state_attributes = self._read_battery()

    async def async_added_to_hass(self) -> None:
        self._update_state()
        await self._async_track_slots(SLOT_ARM, SLOT_STATE, SLOT_BATTERY)

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        eid = self._slot(SLOT_ARM)
        dom = domain_of(eid)
        if dom == "alarm_control_panel":
            await self._forward_service(eid, "alarm_arm_home")
        else:
            await self._forward_service(eid, "turn_on")

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        eid = self._slot(SLOT_ARM)
        dom = domain_of(eid)
        if dom == "alarm_control_panel":
            await self._forward_service(eid, "alarm_arm_away")
        else:
            await self._forward_service(eid, "turn_on")

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        eid = self._slot(SLOT_ARM)
        dom = domain_of(eid)
        if dom == "alarm_control_panel":
            await self._forward_service(eid, "alarm_disarm")
        else:
            await self._forward_service(eid, "turn_off")
