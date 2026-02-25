"""Constants for the HomeKit Entity Architect integration."""

from __future__ import annotations

DOMAIN = "homekit_architect"

# Config entry keys
CONF_TEMPLATE_TYPE = "template_type"
CONF_SLOTS = "slots"
CONF_HOMEKIT_BRIDGE_ENTRY_ID = "homekit_bridge_entry_id"
CONF_AUTOMATED_GHOSTING = "automated_ghosting"
CONF_FRIENDLY_NAME = "friendly_name"

# HomeKit bridge filter key (from homeassistant.helpers.entityfilter)
CONF_FILTER = "filter"
CONF_EXCLUDE_ENTITIES = "exclude_entities"
HOMEKIT_DOMAIN = "homekit"

# Slot keys for templates (used in config and entity state)
SLOT_ACTION = "action"           # Actuator: lock, switch, cover, etc.
SLOT_STATE = "state"             # State sensor: contact, position, etc.
SLOT_BATTERY = "battery"         # Optional: battery level sensor
SLOT_OBSTRUCTION = "obstruction" # Optional: jammed / obstruction sensor
SLOT_ACTUATOR = "actuator"       # Garage: open/close actuator
SLOT_SENSOR_OPENING = "sensor_opening"  # Garage: opening/closing sensor

# Template types -> platform + slot definitions
TEMPLATE_SECURITY_LOCK = "security_lock"
TEMPLATE_GARAGE_DOOR = "garage_door"

TEMPLATES = {
    TEMPLATE_SECURITY_LOCK: {
        "name": "Security Accessory (Smart Lock)",
        "platform": "lock",
        "required_slots": [SLOT_ACTION, SLOT_STATE],
        "optional_slots": [SLOT_BATTERY, SLOT_OBSTRUCTION],
        "slot_labels": {
            SLOT_ACTION: "Lock actuator (switch/lock that moves the bolt)",
            SLOT_STATE: "State sensor (contact or lock state)",
            SLOT_BATTERY: "Battery level sensor (optional)",
            SLOT_OBSTRUCTION: "Jammed/obstruction sensor (optional)",
        },
    },
    TEMPLATE_GARAGE_DOOR: {
        "name": "Garage Door Package",
        "platform": "cover",
        "required_slots": [SLOT_ACTUATOR, SLOT_SENSOR_OPENING],
        "optional_slots": [SLOT_BATTERY, SLOT_OBSTRUCTION],
        "slot_labels": {
            SLOT_ACTUATOR: "Open/Close actuator (switch or cover)",
            SLOT_SENSOR_OPENING: "Opening/Closing state sensor",
            SLOT_BATTERY: "Battery level sensor (optional)",
            SLOT_OBSTRUCTION: "Obstruction sensor (optional)",
        },
    },
}

# Low battery threshold (percent) for StatusLowBattery in HomeKit
DEFAULT_LOW_BATTERY_THRESHOLD = 20
