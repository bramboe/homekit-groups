"""Constants for HomeKit Entity Architect."""

from __future__ import annotations

DOMAIN = "homekit_architect"

# Config entry keys
CONF_TEMPLATE_ID = "template_id"
CONF_SLOTS = "slots"
CONF_HOMEKIT_BRIDGE_ENTRY_ID = "homekit_bridge_entry_id"
CONF_AUTOMATED_GHOSTING = "automated_ghosting"
CONF_ARCHITECT_ENTITY_FRIENDLY_NAME = "friendly_name"

# HomeKit bridge filter keys (must match homekit integration)
CONF_FILTER = "filter"
CONF_INCLUDE_ENTITIES = "include_entities"
CONF_EXCLUDE_ENTITIES = "exclude_entities"
CONF_INCLUDE_DOMAINS = "include_domains"
CONF_EXCLUDE_DOMAINS = "exclude_domains"

# Slot keys used in template definitions and config
SLOT_ACTION = "action_slot"           # Primary actuator (lock, cover, etc.)
SLOT_STATE = "state_slot"             # State sensor (door contact, position)
SLOT_BATTERY = "battery_slot"         # Optional battery level
SLOT_OBSTRUCTION = "obstruction_slot" # Optional obstruction/jam sensor
SLOT_ACTUATOR = "actuator_slot"       # Garage: open/close actuator
SLOT_POSITION_SENSOR = "position_sensor_slot"  # Garage: opening/closing sensor

# Template identifiers and metadata
TEMPLATE_SECURITY_LOCK = "security_lock"
TEMPLATE_GARAGE_DOOR = "garage_door"

TEMPLATES = {
    TEMPLATE_SECURITY_LOCK: {
        "name": "Security Accessory (Smart Lock)",
        "platform": "lock",
        "required_slots": [SLOT_ACTION, SLOT_STATE],
        "optional_slots": [SLOT_BATTERY, SLOT_OBSTRUCTION],
        "slot_labels": {
            SLOT_ACTION: "Lock actuator (switch or lock that moves the bolt)",
            SLOT_STATE: "State sensor (e.g. door contact – closed = locked)",
            SLOT_BATTERY: "Battery level sensor (optional)",
            SLOT_OBSTRUCTION: "Obstruction / jam sensor (optional)",
        },
    },
    TEMPLATE_GARAGE_DOOR: {
        "name": "Garage Door Package",
        "platform": "cover",
        "required_slots": [SLOT_ACTUATOR, SLOT_POSITION_SENSOR],
        "optional_slots": [SLOT_BATTERY],
        "slot_labels": {
            SLOT_ACTUATOR: "Open/Close actuator (cover or switch)",
            SLOT_POSITION_SENSOR: "Opening/Closing sensor (door contact or cover state)",
            SLOT_BATTERY: "Battery sensor (optional)",
        },
    },
}

# Entity registry: we store entity_id in config; entity_registry is used to resolve
# renamed entities via er.async_get(hass).async_get_entity_id(domain, platform, unique_id)
# Our virtual entities use unique_id = f"{DOMAIN}_{entry.entry_id}_{platform}"
