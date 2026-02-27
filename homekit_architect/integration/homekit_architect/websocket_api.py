"""WebSocket API for HomeKit Accessory Architect configuration panel."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.websocket_api import ActiveConnection
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entityfilter import FILTER_SCHEMA, EntityFilter

from .const import (
    CONF_EXCLUDE_DOMAINS,
    CONF_EXCLUDE_ENTITIES,
    CONF_FILTER,
    CONF_INCLUDE_DOMAINS,
    CONF_INCLUDE_ENTITIES,
    DOMAIN,
    TEMPLATES,
)

_LOGGER = logging.getLogger(__name__)

HOMEKIT_DOMAIN = "homekit"
HOMEKIT_MODE_BRIDGE = "bridge"


@callback
def async_register_websocket_handlers(hass: HomeAssistant) -> None:
    """Register WebSocket commands for the Architect panel."""
    websocket_api.async_register_command(hass, ws_list_bridges)
    websocket_api.async_register_command(hass, ws_bridge_entities)
    websocket_api.async_register_command(hass, ws_package_accessory)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/list_bridges",
    }
)
@websocket_api.async_response
async def ws_list_bridges(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return active HomeKit bridges with their current filter (include/exclude)."""
    bridges = []
    for entry in hass.config_entries.async_entries(HOMEKIT_DOMAIN):
        if entry.options.get("homekit_mode") != HOMEKIT_MODE_BRIDGE:
            continue
        filt = entry.options.get(CONF_FILTER) or {}
        bridges.append(
            {
                "entry_id": entry.entry_id,
                "title": entry.title or entry.data.get("name", "HomeKit Bridge"),
                "filter": {
                    "include_entities": filt.get(CONF_INCLUDE_ENTITIES) or [],
                    "exclude_entities": filt.get(CONF_EXCLUDE_ENTITIES) or [],
                    "include_domains": filt.get(CONF_INCLUDE_DOMAINS) or [],
                    "exclude_domains": filt.get(CONF_EXCLUDE_DOMAINS) or [],
                },
            }
        )
    connection.send_result(msg["id"], {"bridges": bridges})


def _entities_exposed_by_bridge_filter(hass: HomeAssistant, filter_config: dict) -> list[str]:
    """Compute entity_ids that pass the bridge's entity filter (would be exposed to HomeKit)."""
    try:
        entity_filter: EntityFilter = FILTER_SCHEMA(filter_config)
    except Exception:
        return []
    reg = er.async_get(hass)
    all_entity_ids = [e.entity_id for e in reg.entities.async_all()]
    return [eid for eid in all_entity_ids if entity_filter(eid)]


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/bridge_entities",
        vol.Required("bridge_entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_bridge_entities(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return entities currently exposed by the given HomeKit bridge (live from filter)."""
    bridge_entry_id = msg["bridge_entry_id"]
    entry = hass.config_entries.async_get_entry(bridge_entry_id)
    if not entry or entry.domain != HOMEKIT_DOMAIN:
        connection.send_error(msg["id"], "not_found", "Bridge not found")
        return
    filt = entry.options.get(CONF_FILTER) or {}
    entity_ids = _entities_exposed_by_bridge_filter(hass, filt)
    reg = er.async_get(hass)
    entities = []
    for eid in sorted(entity_ids):
        e = reg.entities.async_get(eid)
        state = hass.states.get(eid)
        domain = eid.split(".", 1)[0] if "." in eid else ""
        entities.append(
            {
                "entity_id": eid,
                "friendly_name": (e.original_name if e else None) or (state.attributes.get("friendly_name") if state else None) or eid,
                "domain": domain,
                "state": state.state if state else None,
            }
        )
    connection.send_result(msg["id"], {"entities": entities})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/package_accessory",
        vol.Required("bridge_entry_id"): str,
        vol.Required("display_name"): str,
        vol.Required("accessory_type"): str,
        vol.Required("entity_ids"): [str],
        vol.Required("slot_mapping"): dict,
        vol.Optional("hide_sources", default=True): bool,
    }
)
@websocket_api.async_response
async def ws_package_accessory(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Create an Architect accessory from selected entities and optionally apply ghosting."""
    bridge_entry_id = msg["bridge_entry_id"]
    display_name = (msg["display_name"] or "").strip() or "Accessory"
    accessory_type = msg["accessory_type"]
    entity_ids = list(msg["entity_ids"]) if msg.get("entity_ids") else []
    slot_mapping = msg.get("slot_mapping") or {}
    hide_sources = msg.get("hide_sources", True)

    template_id = _accessory_type_to_template_id(accessory_type)
    if not template_id:
        connection.send_error(msg["id"], "invalid_type", f"Unknown accessory type: {accessory_type}")
        return

    template = TEMPLATES.get(template_id)
    if not template:
        connection.send_error(msg["id"], "invalid_template", "Template not found")
        return

    # Build slots from slot_mapping; ensure required slots are filled from entity_ids if not mapped
    slots = _build_slots_from_mapping(template, slot_mapping, entity_ids)
    for req in template["required_slots"]:
        if not slots.get(req):
            connection.send_error(
                msg["id"],
                "missing_slot",
                f"Required slot '{req}' must be assigned to an entity.",
            )
            return

    # Create config entry via flow (panel source) - one-step create, no UI
    # Panel data in context so async_step_user can forward to async_step_panel
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": "panel",
            "panel_package": True,
            "panel_data": {
                "template_id": template_id,
                "slots": slots,
                "homekit_bridge_entry_id": bridge_entry_id,
                "automated_ghosting": hide_sources,
                "friendly_name": display_name,
            },
        },
    )

    if result["type"] != "create_entry":
        reason = getattr(result, "reason", None) or result.get("reason", "Could not create accessory")
        connection.send_error(msg["id"], "create_failed", str(reason))
        return

    entry = result["result"]
    connection.send_result(
        msg["id"],
        {
            "entry_id": entry.entry_id,
            "title": entry.title,
        },
    )


def _accessory_type_to_template_id(accessory_type: str) -> str | None:
    """Map UI accessory type (fan, lock, cover, light) to our template_id."""
    at = (accessory_type or "").lower()
    if at in ("lock", "security", "smart_lock"):
        return "security_lock"
    if at in ("cover", "garage_door", "garage"):
        return "garage_door"
    if at in ("fan", "ventilation") and "fan" in TEMPLATES:
        return "fan"
    if at in ("light", "switch") and "light" in TEMPLATES:
        return "light"
    return None


def _build_slots_from_mapping(
    template: dict,
    slot_mapping: dict[str, str],
    entity_ids: list[str],
) -> dict[str, str]:
    """Build slots dict from panel slot_mapping; suggest defaults from entity_ids for unmapped slots."""
    slots = dict(slot_mapping)
    required = set(template["required_slots"])
    optional = set(template.get("optional_slots") or [])
    used = set(slots.values())
    remaining = [e for e in entity_ids if e and e not in used]
    for slot in required | optional:
        if slot in slots and slots[slot]:
            continue
        if remaining:
            slots[slot] = remaining.pop(0)
    return {k: v for k, v in slots.items() if v and k in required | optional}
