"""Virtual lock platform for the 'lock' template.

Template pattern: state from slot entity; lock/unlock forwarded by domain
(lock.lock/unlock or switch/light turn_off/turn_on for single-entity lock)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.lock import LockEntity, LockState
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base import ArchitectBase, domain_of
from .const import SLOT_ACTION, SLOT_BATTERY, SLOT_OBSTRUCTION, SLOT_STATE, TEMPLATES

HANDLED_TEMPLATES = ("lock",)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    tid = entry.data.get("template_id")
    if tid not in HANDLED_TEMPLATES:
        return
    slots = entry.data.get("slots") or {}
    if not slots.get(SLOT_ACTION) or not slots.get(SLOT_STATE):
        return
    async_add_entities([ArchitectLock(hass, entry)])


class ArchitectLock(ArchitectBase, LockEntity):

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._architect_init(hass, entry, "lock")

    @callback
    def _update_state(self) -> None:
        st = self.hass.states.get(self._slot(SLOT_STATE))
        val = st.state if st else STATE_UNKNOWN
        if val in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self._attr_is_locked = None
        else:
            self._attr_is_locked = val == STATE_ON

        obs = self.hass.states.get(self._slot(SLOT_OBSTRUCTION)) if self._slot(SLOT_OBSTRUCTION) else None
        self._attr_is_jammed = obs is not None and obs.state == STATE_ON

        self._attr_extra_state_attributes = self._read_battery()

    async def async_added_to_hass(self) -> None:
        self._update_state()
        await self._async_track_slots(SLOT_STATE, SLOT_OBSTRUCTION, SLOT_BATTERY)

    async def async_lock(self, **kwargs: Any) -> None:
        eid = self._slot(SLOT_ACTION)
        svc = "lock" if domain_of(eid) == "lock" else "turn_on"
        await self._forward_service(eid, svc)

    async def async_unlock(self, **kwargs: Any) -> None:
        eid = self._slot(SLOT_ACTION)
        svc = "unlock" if domain_of(eid) == "lock" else "turn_off"
        await self._forward_service(eid, svc)
