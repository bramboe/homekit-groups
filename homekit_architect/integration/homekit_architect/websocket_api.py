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

# Fallback multi_service template (same slot keys as const) so package_accessory
# accepts "multi_service" even when const.py is from an older install.
_MULTI_SERVICE_TEMPLATE_FALLBACK = {
    "name": "Multi-Service",
    "platforms": [
        "alarm_control_panel",
        "binary_sensor",
        "camera",
        "climate",
        "cover",
        "fan",
        "humidifier",
        "light",
        "lock",
        "media_player",
        "sensor",
        "switch",
    ],
    "required_slots": ["primary_slot", "secondary_slot"],
    "optional_slots": [
        "tertiary_slot",
        "quaternary_slot",
        "quinary_slot",
        "senary_slot",
        "septenary_slot",
        "octonary_slot",
    ],
    "slot_labels": {
        "primary_slot": "Control 1",
        "secondary_slot": "Control 2",
        "tertiary_slot": "Control 3",
        "quaternary_slot": "Control 4",
        "quinary_slot": "Control 5",
        "senary_slot": "Control 6",
        "septenary_slot": "Control 7",
        "octonary_slot": "Control 8",
    },
}
_MULTI_SERVICE_DOMAINS = {
    "alarm_control_panel",
    "binary_sensor",
    "camera",
    "climate",
    "cover",
    "fan",
    "humidifier",
    "input_boolean",
    "light",
    "lock",
    "media_player",
    "sensor",
    "switch",
}

HOMEKIT_DOMAIN = "homekit"
HOMEKIT_MODE_BRIDGE = "bridge"


@callback
def async_register_websocket_handlers(hass: HomeAssistant) -> None:
    """Register WebSocket commands for the Architect panel."""
    websocket_api.async_register_command(hass, ws_list_bridges)
    websocket_api.async_register_command(hass, ws_bridge_entities)
    websocket_api.async_register_command(hass, ws_list_templates)
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
        mode = entry.options.get("homekit_mode") or entry.data.get("homekit_mode", "bridge")
        if mode == "accessory":
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


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/list_templates",
    }
)
@callback
def ws_list_templates(
    hass: HomeAssistant,
    connection: ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return template definitions with required/optional slots for slot-assignment UI."""
    templates = []
    for tid, t in TEMPLATES.items():
        labels = t.get("slot_labels") or {}
        required = [
            {"key": k, "label": labels.get(k, k)}
            for k in (t.get("required_slots") or [])
        ]
        optional = [
            {"key": k, "label": labels.get(k, k)}
            for k in (t.get("optional_slots") or [])
        ]
        templates.append({
            "id": tid,
            "name": t.get("name", tid),
            "required_slots": required,
            "optional_slots": optional,
        })
    connection.send_result(msg["id"], {"templates": templates})


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

    # Build slots from slot_mapping; ensure required slots are filled from entity_ids if not mapped.
    # If some required slots are still missing (because the user picked an advanced type but did not
    # provide matching entities), gracefully fall back to a simple \"switch\"-style template that only
    # needs a single source entity.
    slots = _build_slots_from_mapping(template, slot_mapping, entity_ids)
    missing_required = [req for req in template["required_slots"] if not slots.get(req)]

    if missing_required:
        # Try to pick a simpler template based on the selected entities, but at minimum
        # use a plain \"switch\" template which only requires one entity.
        fallback_template_id = _pick_fallback_template_id(entity_ids)
        if fallback_template_id and fallback_template_id in TEMPLATES:
            template_id = fallback_template_id
            template = TEMPLATES[template_id]
            slots = _build_slots_from_mapping(template, {}, entity_ids)
            # After fallback, if we STILL can't satisfy required slots, abort.
            missing_required = [req for req in template["required_slots"] if not slots.get(req)]
            if missing_required:
                connection.send_error(
                    msg["id"],
                    "missing_slot",
                    f"Required slot(s) {', '.join(missing_required)} must be assigned to an entity.",
                )
                return
        else:
            connection.send_error(
                msg["id"],
                "missing_slot",
                f"Required slot(s) {', '.join(missing_required)} must be assigned to an entity.",
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


def _ensure_multi_service_template() -> None:
    """Inject multi_service into TEMPLATES if missing (e.g. older integration install)."""
    if "multi_service" not in TEMPLATES:
        TEMPLATES["multi_service"] = dict(_MULTI_SERVICE_TEMPLATE_FALLBACK)


def _accessory_type_to_template_id(accessory_type: str) -> str | None:
    """Validate that the accessory type is a known template."""
    tid = (accessory_type or "").lower().strip().replace("-", "_")
    if tid == "multi_service":
        _ensure_multi_service_template()
    return tid if tid in TEMPLATES else None


def _pick_fallback_template_id(entity_ids: list[str]) -> str | None:
    """Pick a simple template id that we can always satisfy from the selected entities."""
    if not entity_ids:
        return None

    domains = [eid.split(".", 1)[0] for eid in entity_ids if "." in eid]

    # Multiple entities (2–8) of any supported type → generic multi-service
    if len(entity_ids) >= 2:
        _ensure_multi_service_template()
        if "multi_service" in TEMPLATES and (set(domains) & _MULTI_SERVICE_DOMAINS):
            return "multi_service"
    # Prefer Fan + Light combo if both fan and light are selected
    if "fan" in domains and "light" in domains and "fan_light" in TEMPLATES:
        return "fan_light"
    # Prefer a light-style template if there is any light entity
    if "light" in domains and "lightbulb" in TEMPLATES:
        return "lightbulb"
    # Prefer a lock template if there is a lock
    if "lock" in domains and "lock" in TEMPLATES:
        return "lock"
    # Prefer a fan template if there is a fan
    if "fan" in domains and "fan" in TEMPLATES:
        return "fan"

    # Default fallback is a simple switch-style template – works for almost anything
    if "switch" in TEMPLATES:
        return "switch"
    return None


def _build_slots_from_mapping(
    template: dict,
    slot_mapping: dict[str, str],
    entity_ids: list[str],
) -> dict[str, str]:
    """Build slots dict from panel slot_mapping.

    IMPORTANT: This helper is intentionally permissive – it will happily reuse the
    same underlying entity for multiple slots if needed. The goal is that as
    long as the user selected at least one entity, ALL required slots will be
    populated so creation cannot fail with \"missing slot\" errors.
    """
    slots = dict(slot_mapping)
    required = set(template["required_slots"])
    optional = set(template.get("optional_slots") or [])
    all_ids = [e for e in entity_ids if e]

    for slot in required | optional:
        if slots.get(slot):
            continue
        if all_ids:
            # Always fall back to the first selected entity; re‑using the same
            # source entity for multiple slots is acceptable for our purposes.
            slots[slot] = all_ids[0]

    return {k: v for k, v in slots.items() if v and k in required | optional}
