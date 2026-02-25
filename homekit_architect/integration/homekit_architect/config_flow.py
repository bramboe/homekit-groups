"""Config flow for HomeKit Entity Architect."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .const import (
    CONF_ARCHITECT_ENTITY_FRIENDLY_NAME,
    CONF_AUTOMATED_GHOSTING,
    CONF_HOMEKIT_BRIDGE_ENTRY_ID,
    CONF_SLOTS,
    CONF_TEMPLATE_ID,
    DOMAIN,
    TEMPLATES,
)

HOMEKIT_DOMAIN = "homekit"
HOMEKIT_MODE_BRIDGE = "bridge"


def _homekit_bridge_entries(hass: HomeAssistant) -> list[tuple[str, str]]:
    """Return list of (entry_id, title) for HomeKit bridges (bridge mode only)."""
    result = []
    for entry in hass.config_entries.async_entries(HOMEKIT_DOMAIN):
        if entry.options.get("homekit_mode") == HOMEKIT_MODE_BRIDGE:
            result.append((entry.entry_id, entry.title or entry.data.get("name", entry.entry_id)))
    return result


class HomeKitArchitectConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HomeKit Entity Architect."""

    VERSION = 1

    def __init__(self) -> None:
        self._template_id: str | None = None
        self._slots: dict[str, str] = {}
        self._friendly_name: str = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Template selection."""
        if user_input is not None:
            self._template_id = user_input[CONF_TEMPLATE_ID]
            return await self.async_step_slots()

        template_options = {tid: t["name"] for tid, t in TEMPLATES.items()}
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TEMPLATE_ID): vol.In(template_options),
                }
            ),
        )

    async def async_step_slots(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Entity assignment to slots (dynamic per template)."""
        template = TEMPLATES.get(self._template_id or "")
        if not template:
            return self.async_abort(reason="invalid_template")

        if user_input is not None:
            self._slots = {k: v for k, v in user_input.items() if v and k in (
                template["required_slots"] + template["optional_slots"]
            )}
            # Validate required slots
            for slot in template["required_slots"]:
                if not self._slots.get(slot):
                    return self.async_show_form(
                        step_id="slots",
                        data_schema=self._slots_schema(template),
                        errors={slot: "required"},
                    )
            return await self.async_step_bridge()

        return self.async_show_form(
            step_id="slots",
            data_schema=self._slots_schema(template),
        )

    def _slots_schema(self, template: dict) -> vol.Schema:
        """Build schema with entity selectors for required + optional slots."""
        schema = {}
        for slot in template["required_slots"] + template["optional_slots"]:
            required = slot in template["required_slots"]
            key = vol.Required(slot) if required else vol.Optional(slot, default="")
            schema[key] = selector.EntitySelector(
                selector.EntitySelectorConfig(
                    multiple=False,
                    include_entities=self._slots.get(slot) or None,
                )
            )
        return vol.Schema(schema)

    async def async_step_bridge(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick target HomeKit Bridge."""
        if user_input is not None:
            self._bridge_entry_id = user_input.get(CONF_HOMEKIT_BRIDGE_ENTRY_ID)
            return await self.async_step_ghosting()

        bridges = _homekit_bridge_entries(self.hass)
        if not bridges:
            return self.async_abort(reason="no_bridge")

        return self.async_show_form(
            step_id="bridge",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOMEKIT_BRIDGE_ENTRY_ID,
                        default=bridges[0][0] if bridges else "",
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[{"value": eid, "label": title} for eid, title in bridges],
                            mode="dropdown",
                        )
                    ),
                }
            ),
        )

    async def async_step_ghosting(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ghosting toggle and optional friendly name."""
        template = TEMPLATES.get(self._template_id or "")
        if not template:
            return self.async_abort(reason="invalid_template")

        if user_input is not None:
            friendly = (user_input.get(CONF_ARCHITECT_ENTITY_FRIENDLY_NAME) or "").strip()
            data = {
                CONF_TEMPLATE_ID: self._template_id,
                CONF_SLOTS: self._slots,
                CONF_HOMEKIT_BRIDGE_ENTRY_ID: getattr(self, "_bridge_entry_id", ""),
                CONF_AUTOMATED_GHOSTING: user_input.get(CONF_AUTOMATED_GHOSTING, True),
                CONF_ARCHITECT_ENTITY_FRIENDLY_NAME: friendly or template["name"],
            }
            return self.async_create_entry(
                title=friendly or template["name"],
                data=data,
            )

        return self.async_show_form(
            step_id="ghosting",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_AUTOMATED_GHOSTING,
                        default=True,
                    ): selector.BooleanSelector(),
                    vol.Optional(
                        CONF_ARCHITECT_ENTITY_FRIENDLY_NAME,
                        default=self._friendly_name or template["name"],
                    ): selector.TextSelector(),
                }
            ),
        )
