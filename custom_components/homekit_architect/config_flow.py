"""Config flow for the HomeKit Entity Architect integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_AUTOMATED_GHOSTING,
    CONF_FRIENDLY_NAME,
    CONF_HOMEKIT_BRIDGE_ENTRY_ID,
    CONF_SLOTS,
    CONF_TEMPLATE_TYPE,
    DOMAIN,
    HOMEKIT_DOMAIN,
    TEMPLATES,
)

_LOGGER = logging.getLogger(__name__)


def _get_homekit_bridges(hass: HomeAssistant) -> list[tuple[str, str]]:
    """Return list of (entry_id, title) for all HomeKit bridge config entries."""
    return [
        (entry.entry_id, entry.title or entry.data.get("name", "HomeKit Bridge"))
        for entry in hass.config_entries.async_entries(HOMEKIT_DOMAIN)
    ]


class HomeKitArchitectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HomeKit Entity Architect."""

    VERSION = 1

    def __init__(self) -> None:
        self._template_type: str | None = None
        self._slots: dict[str, str] = {}
        self._bridge_entry_id: str = ""
        self._automated_ghosting: bool = True

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return options flow handler."""
        return HomeKitArchitectOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Start the config flow: first step is template selection."""
        if user_input is not None:
            self._template_type = user_input[CONF_TEMPLATE_TYPE]
            return await self.async_step_slots()

        bridges = _get_homekit_bridges(self.hass)
        if not bridges:
            return self.async_abort(reason="no_bridges")

        template_options = [
            {"value": key, "label": t["name"]} for key, t in TEMPLATES.items()
        ]
        schema = vol.Schema({
            vol.Required(CONF_TEMPLATE_TYPE): SelectSelector(
                SelectSelectorConfig(
                    options=template_options,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
        })
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_slots(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Assign entities to slots."""
        if self._template_type is None:
            return self.async_abort(reason="no_bridges")

        template = TEMPLATES[self._template_type]
        if user_input is not None:
            slots = {}
            for slot in template["required_slots"] + template["optional_slots"]:
                val = user_input.get(slot)
                entity_id = None
                if isinstance(val, str) and val.strip():
                    entity_id = val.strip()
                elif isinstance(val, dict) and val.get(CONF_ENTITY_ID):
                    entity_id = val[CONF_ENTITY_ID]
                elif isinstance(val, list) and val:
                    entity_id = val[0] if isinstance(val[0], str) else (val[0].get(CONF_ENTITY_ID) if isinstance(val[0], dict) else None)
                if entity_id:
                    slots[slot] = entity_id
            for req in template["required_slots"]:
                if req not in slots or not slots[req]:
                    return self.async_show_form(
                        step_id="slots",
                        data_schema=vol.Schema(self._slots_schema()),
                        errors={"base": "required_slots"},
                    )
            self._slots = slots
            return await self.async_step_bridge()

        return self.async_show_form(
            step_id="slots",
            data_schema=vol.Schema(self._slots_schema()),
        )

    def _slots_schema(self) -> dict[str, Any]:
        """Build schema for slot step (entity selectors for each slot)."""
        template = TEMPLATES[self._template_type]
        schema = {}
        for slot in template["required_slots"]:
            schema[vol.Required(slot)] = EntitySelector(EntitySelectorConfig(multiple=False))
        for slot in template["optional_slots"]:
            schema[vol.Optional(slot)] = EntitySelector(EntitySelectorConfig(multiple=False))
        return schema

    async def async_step_bridge(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Select HomeKit Bridge and ghosting option."""
        if user_input is not None:
            bridge_entry_id = user_input[CONF_HOMEKIT_BRIDGE_ENTRY_ID]
            if isinstance(bridge_entry_id, list) and bridge_entry_id:
                bridge_entry_id = bridge_entry_id[0]
            self._bridge_entry_id = bridge_entry_id
            self._automated_ghosting = user_input.get(CONF_AUTOMATED_GHOSTING, True)
            return await self.async_step_name()

        bridges = _get_homekit_bridges(self.hass)
        if not bridges:
            return self.async_abort(reason="no_bridges")

        schema = vol.Schema({
            vol.Required(CONF_HOMEKIT_BRIDGE_ENTRY_ID): SelectSelector(
                SelectSelectorConfig(
                    options=[{"value": eid, "label": title} for eid, title in bridges],
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(CONF_AUTOMATED_GHOSTING, default=True): bool,
        })
        return self.async_show_form(step_id="bridge", data_schema=schema)

    async def async_step_name(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Optional friendly name, then create entry."""
        if user_input is not None:
            friendly_name = (user_input.get(CONF_FRIENDLY_NAME) or "").strip()
            if not friendly_name and self._template_type:
                friendly_name = TEMPLATES[self._template_type]["name"]
            title = friendly_name or "HomeKit Architect"
            data = {
                CONF_TEMPLATE_TYPE: self._template_type,
                CONF_SLOTS: self._slots,
                CONF_HOMEKIT_BRIDGE_ENTRY_ID: self._bridge_entry_id,
                CONF_AUTOMATED_GHOSTING: self._automated_ghosting,
                CONF_FRIENDLY_NAME: friendly_name,
            }
            return self.async_create_entry(title=title, data=data)

        template = TEMPLATES.get(self._template_type, {})
        default_name = template.get("name", "HomeKit Architect")
        schema = vol.Schema({
            vol.Optional(CONF_FRIENDLY_NAME, default=default_name): str,
        })
        return self.async_show_form(step_id="name", data_schema=schema)


class HomeKitArchitectOptionsFlow(config_entries.OptionsFlow):
    """Options flow for editing an existing entry."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage options: re-run slot + bridge steps or just bridge/ghosting."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
            description_placeholders={"entry_title": self.config_entry.title},
        )
