"""Config flow for HomeKit Entity Architect (app: one entry, multiple accessory groups)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .const import (
    CONF_APPLY_GHOST_HIDE,
    CONF_BRIDGE_ID,
    CONF_ENTITY_NAME,
    CONF_GROUPS,
    CONF_GROUP_ID,
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


def _group_from_wizard(
    target_domain: str,
    entity_name: str,
    member_entities: dict[str, str],
    bridge_id: str,
    apply_ghost_hide: bool,
    group_id: str | None = None,
) -> dict[str, Any]:
    """Build a group dict from wizard data."""
    return {
        CONF_GROUP_ID: group_id or uuid.uuid4().hex,
        CONF_TARGET_DOMAIN: target_domain,
        CONF_ENTITY_NAME: entity_name,
        CONF_MEMBER_ENTITIES: member_entities,
        CONF_BRIDGE_ID: bridge_id,
        CONF_APPLY_GHOST_HIDE: apply_ghost_hide,
    }


class HomeKitArchitectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Single-app config flow: one entry; first run creates the app with one group."""

    VERSION = 1

    def __init__(self) -> None:
        self._target_domain: str | None = None
        self._entity_name: str | None = None
        self._member_entities: dict[str, str] = {}
        self._bridge_id: str | None = None
        self._apply_ghost_hide: bool = True
        self._editing_group_id: str | None = None  # set in options flow for edit

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Start: ensure single app entry; then choose accessory type."""
        # Only one integration entry (the app)
        if self.hass.config_entries.async_entries(DOMAIN):
            return self.async_abort(reason="already_configured")

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
            self._entity_name = user_input.get(CONF_ENTITY_NAME) or "Accessory"
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
                    default=self._entity_name or "Accessory",
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
        """Create the single app config entry with one group."""
        group = _group_from_wizard(
            self._target_domain or "fan",
            self._entity_name or "Accessory",
            self._member_entities,
            self._bridge_id or "",
            self._apply_ghost_hide,
            group_id=self._editing_group_id,
        )
        return self.async_create_entry(
            title="HomeKit Entity Architect",
            data={CONF_GROUPS: [group]},
        )


@callback
def async_get_options_flow(
    config_entry: ConfigEntry,
) -> HomeKitArchitectOptionsFlow:
    """Options flow: add / edit / remove accessory groups."""
    return HomeKitArchitectOptionsFlow(config_entry)


class HomeKitArchitectOptionsFlow(config_entries.OptionsFlow):
    """Manage accessory groups (add, edit, remove)."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry
        self._target_domain: str | None = None
        self._entity_name: str | None = None
        self._member_entities: dict[str, str] = {}
        self._bridge_id: str | None = None
        self._apply_ghost_hide: bool = True
        self._editing_group_id: str | None = None

    def _groups(self) -> list[dict[str, Any]]:
        return list(self.config_entry.data.get(CONF_GROUPS) or [])

    def _save_groups(self, groups: list[dict[str, Any]]) -> config_entries.ConfigFlowResult:
        new_data = {**self.config_entry.data, CONF_GROUPS: groups}
        self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
        self.hass.async_create_task(
            self.hass.config_entries.async_reload(self.config_entry.entry_id)
        )
        return self.async_create_entry(title="", data={})

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Menu: add group or choose group to edit/remove."""
        groups = self._groups()
        if user_input is not None:
            choice = user_input.get("choice")
            if choice == "add":
                return await self.async_step_accessory_type()
            if choice and choice.startswith("edit_"):
                self._editing_group_id = choice.replace("edit_", "")
                g = next((x for x in groups if x.get(CONF_GROUP_ID) == self._editing_group_id), None)
                if g:
                    self._target_domain = g.get(CONF_TARGET_DOMAIN)
                    self._entity_name = g.get(CONF_ENTITY_NAME)
                    self._member_entities = dict(g.get(CONF_MEMBER_ENTITIES) or {})
                    self._bridge_id = g.get(CONF_BRIDGE_ID)
                    self._apply_ghost_hide = g.get(CONF_APPLY_GHOST_HIDE, True)
                    return await self.async_step_entity_mapping()
            if choice and choice.startswith("remove_"):
                self._editing_group_id = choice.replace("remove_", "")
                new_groups = [x for x in groups if x.get(CONF_GROUP_ID) != self._editing_group_id]
                return self._save_groups(new_groups)

        options = [("add", "Add accessory group")]
        for g in groups:
            gid = g.get(CONF_GROUP_ID) or ""
            name = g.get(CONF_ENTITY_NAME) or g.get(CONF_TARGET_DOMAIN) or "Group"
            options.append((f"edit_{gid}", f"Edit: {name}"))
            options.append((f"remove_{gid}", f"Remove: {name}"))

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("choice"): vol.In({k: v for k, v in options}),
                }
            ),
        )

    async def async_step_accessory_type(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Choose accessory type (add-group path)."""
        if user_input is not None:
            self._target_domain = user_input[CONF_TARGET_DOMAIN]
            return await self.async_step_entity_mapping()

        return self.async_show_form(
            step_id="accessory_type",
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
        """Map entities (add or edit)."""
        if user_input is not None:
            self._entity_name = user_input.get(CONF_ENTITY_NAME) or "Accessory"
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
                    default=self._entity_name or "Accessory",
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
                    )
                ),
            }
        )

    async def async_step_bridge_selection(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Bridge and Ghost (add or edit)."""
        bridges = _get_homekit_bridges(self.hass)
        if not bridges:
            return self.async_abort(reason="no_bridges")

        if user_input is not None:
            self._bridge_id = user_input.get(CONF_BRIDGE_ID)
            self._apply_ghost_hide = user_input.get(CONF_APPLY_GHOST_HIDE, True)
            if self._bridge_id and self._bridge_id not in [b[0] for b in bridges]:
                return self.async_show_form(
                    step_id="bridge_selection",
                    data_schema=self._schema_bridge(bridges),
                    errors={"base": "bridge_not_found"},
                )
            return self._save_group(bridges)

        return self.async_show_form(
            step_id="bridge_selection",
            data_schema=self._schema_bridge(bridges),
        )

    def _schema_bridge(
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

    def _save_group(
        self,
        bridges: list[tuple[str, str]],
    ) -> config_entries.ConfigFlowResult:
        groups = self._groups()
        new_group = _group_from_wizard(
            self._target_domain or "fan",
            self._entity_name or "Accessory",
            self._member_entities,
            self._bridge_id or "",
            self._apply_ghost_hide,
            group_id=self._editing_group_id,
        )
        if self._editing_group_id:
            groups = [g for g in groups if g.get(CONF_GROUP_ID) != self._editing_group_id]
        groups.append(new_group)
        return self._save_groups(groups)
