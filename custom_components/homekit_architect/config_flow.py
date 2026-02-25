"""Config flow for HomeKit Entity Architect."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
)

from .const import (
    CONF_APPLY_GHOST_HIDE,
    CONF_BRIDGE_ID,
    CONF_ENTITY_NAME,
    CONF_MEMBER_ENTITIES,
    CONF_TARGET_DOMAIN,
    DOMAIN,
    FAN_SLOT_BATTERY,
    FAN_SLOT_SPEED,
    HOMEKIT_DOMAIN,
    TARGET_DOMAINS,
)

_LOGGER = logging.getLogger(__name__)


def _get_homekit_bridges(hass: HomeAssistant) -> list[tuple[str, str]]:
    """Return list of (entry_id, title) for active HomeKit bridges."""
    bridges = []
    for entry in hass.config_entries.async_entries(HOMEKIT_DOMAIN):
        title = entry.title or entry.entry_id
        bridges.append((entry.entry_id, title))
    return bridges


class HomeKitArchitectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HomeKit Entity Architect."""

    VERSION = 1

    def __init__(self) -> None:
        self._target_domain: str | None = None
        self._entity_name: str | None = None
        self._member_entities: dict[str, str] = {}
        self._bridge_id: str | None = None
        self._apply_ghost_hide: bool = True

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Start the flow: choose accessory type."""
        if user_input is not None:
            self._target_domain = user_input[CONF_TARGET_DOMAIN]
            return await self.async_step_entity_mapping()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TARGET_DOMAIN): vol.In(
                        {d: d.capitalize() for d in TARGET_DOMAINS}
                    ),
                }
            ),
        )

    async def async_step_entity_mapping(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Map source entities to the virtual accessory."""
        if user_input is not None:
            self._entity_name = user_input.get(CONF_ENTITY_NAME) or "Architect Fan"
            self._member_entities = {
                FAN_SLOT_SPEED: user_input.get(FAN_SLOT_SPEED) or "",
                FAN_SLOT_BATTERY: user_input.get(FAN_SLOT_BATTERY) or "",
            }
            self._member_entities = {k: v for k, v in self._member_entities.items() if v}
            if not self._member_entities.get(FAN_SLOT_SPEED):
                return self.async_show_form(
                    step_id="entity_mapping",
                    data_schema=self._schema_entity_mapping(),
                    errors={"base": "invalid_entity"},
                )
            return await self.async_step_bridge_selection()

        return self.async_show_form(
            step_id="entity_mapping",
            data_schema=self._schema_entity_mapping(),
        )

    def _schema_entity_mapping(self) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(
                    CONF_ENTITY_NAME,
                    default=self._entity_name or "Architect Fan",
                ): str,
                vol.Required(
                    FAN_SLOT_SPEED,
                  default=self._member_entities.get(FAN_SLOT_SPEED),
                ): EntitySelector(
                    EntitySelectorConfig(
                        multiple=False,
                        filter=[
                            {"domain": "light"},
                            {"domain": "fan"},
                            {"domain": "switch"},
                        ],
                    )
                ),
                vol.Optional(
                    FAN_SLOT_BATTERY,
                    default=self._member_entities.get(FAN_SLOT_BATTERY) or "",
                ): EntitySelector(
                    EntitySelectorConfig(
                        multiple=False,
                        filter=[{"domain": "sensor"}],
                        include_entities=[],
                    )
                ),
            }
        )

    async def async_step_bridge_selection(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Select HomeKit Bridge and Ghost Hide option."""
        bridges = _get_homekit_bridges(self.hass)
        if not bridges:
            return self.async_abort(reason="no_bridges")

        if user_input is not None:
            self._bridge_id = user_input.get(CONF_BRIDGE_ID)
            self._apply_ghost_hide = user_input.get(CONF_APPLY_GHOST_HIDE, True)
            if self._bridge_id and self._bridge_id not in [b[0] for b in bridges]:
                return self.async_show_form(
                    step_id="bridge_selection",
                    data_schema=self._schema_bridge_selection(bridges),
                    errors={"base": "bridge_not_found"},
                )
            return self._create_entry()

        return self.async_show_form(
            step_id="bridge_selection",
            data_schema=self._schema_bridge_selection(bridges),
        )

    def _schema_bridge_selection(
        self,
        bridges: list[tuple[str, str]],
    ) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(
                    CONF_BRIDGE_ID,
                    default=self._bridge_id or (bridges[0][0] if bridges else None),
                ): vol.In({eid: title for eid, title in bridges}),
                vol.Required(
                    CONF_APPLY_GHOST_HIDE,
                    default=self._apply_ghost_hide,
                ): bool,
            }
        )

    def _create_entry(self) -> config_entries.ConfigFlowResult:
        """Create the config entry."""
        data = {
            CONF_TARGET_DOMAIN: self._target_domain or "fan",
            CONF_ENTITY_NAME: self._entity_name or "Architect Fan",
            CONF_MEMBER_ENTITIES: self._member_entities,
            CONF_BRIDGE_ID: self._bridge_id or "",
            CONF_APPLY_GHOST_HIDE: self._apply_ghost_hide,
        }
        return self.async_create_entry(
            title=self._entity_name or "HomeKit Architect",
            data=data,
        )


@callback
def async_get_options_flow(
    config_entry: ConfigEntry,
) -> HomeKitArchitectOptionsFlow:
    """Return options flow handler."""
    return HomeKitArchitectOptionsFlow(config_entry)


class HomeKitArchitectOptionsFlow(config_entries.OptionsFlow):
    """Options flow for reconfiguring Ghost Hide etc."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            # Options are stored in entry.data for this integration; update and reload
            new_data = {**self.config_entry.data, **user_input}
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=new_data,
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_APPLY_GHOST_HIDE,
                        default=self.config_entry.data.get(CONF_APPLY_GHOST_HIDE, True),
                    ): bool,
                }
            ),
        )
