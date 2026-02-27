"""Shared base for all Architect virtual entities."""

from __future__ import annotations

from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_ARCHITECT_ENTITY_FRIENDLY_NAME,
    CONF_SLOTS,
    DOMAIN,
    SLOT_BATTERY,
    TEMPLATES,
)


def domain_of(entity_id: str) -> str:
    """Extract domain from entity_id."""
    return entity_id.split(".", 1)[0] if "." in entity_id else ""


class ArchitectBase:
    """Mixin that provides common functionality for all virtual entities."""

    _attr_has_entity_name = True

    def _architect_init(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        platform: str,
        slot_key: str | None = None,
    ) -> None:
        self.hass = hass
        self._entry = entry
        template_id = entry.data.get("template_id", "")
        self._template = TEMPLATES.get(template_id, {})
        self._slots: dict[str, str] = entry.data.get(CONF_SLOTS) or {}
        self._multi_slot_key: str | None = slot_key

        friendly = (
            entry.data.get(CONF_ARCHITECT_ENTITY_FRIENDLY_NAME)
            or self._template.get("name", "Accessory")
        )
        if slot_key:
            self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{platform}_{slot_key}"
        else:
            self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{platform}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": friendly,
            "manufacturer": "HomeKit Architect",
            "model": self._template.get("name", template_id),
        }
        self._attr_name = friendly

    def _slot(self, key: str) -> str:
        """Get entity_id for a slot, or empty string."""
        return self._slots.get(key, "")

    @callback
    def _read_battery(self) -> dict:
        """Return extra_state_attributes dict with battery level (if available)."""
        attrs: dict = {}
        bat_id = self._slot(SLOT_BATTERY)
        if bat_id:
            st = self.hass.states.get(bat_id)
            if st and st.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                try:
                    attrs[ATTR_BATTERY_LEVEL] = int(float(st.state))
                except (TypeError, ValueError):
                    pass
        return attrs

    def _tracked_entities(self, *slot_keys: str) -> list[str]:
        """Return list of non-empty entity_ids for the given slots."""
        return [eid for k in slot_keys if (eid := self._slot(k))]

    async def _async_track_slots(self, *slot_keys: str) -> None:
        """Subscribe to state changes of the given slot entities."""
        entities = self._tracked_entities(*slot_keys)
        if not entities:
            return

        @callback
        def _on_change(event):
            self._update_state()
            self.async_write_ha_state()

        self.async_on_remove(
            async_track_state_change_event(self.hass, entities, _on_change)
        )

    async def _forward_service(self, entity_id: str, service: str, data: dict | None = None) -> None:
        """Call a service on a source entity."""
        domain = domain_of(entity_id)
        if not domain:
            return
        svc_data = {"entity_id": entity_id}
        if data:
            svc_data.update(data)
        await self.hass.services.async_call(domain, service, svc_data, blocking=True)
