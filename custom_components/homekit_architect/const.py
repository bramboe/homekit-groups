"""Constants for the HomeKit Entity Architect integration."""

DOMAIN = "homekit_architect"

# Config entry keys
CONF_TARGET_DOMAIN = "target_domain"
CONF_MEMBER_ENTITIES = "member_entities"
CONF_BRIDGE_ID = "bridge_id"
CONF_APPLY_GHOST_HIDE = "apply_ghost_hide"
CONF_ENTITY_NAME = "entity_name"

# Target domain options (Phase 1: Fan only; Phase 3: climate, lock)
TARGET_DOMAINS = ["fan"]

# Fan slot keys for member entity mapping
FAN_SLOT_SPEED = "speed_entity"  # Light/dimmer or fan for percentage
FAN_SLOT_BATTERY = "battery_sensor"  # Optional sensor for battery

# HomeKit bridge domain
HOMEKIT_DOMAIN = "homekit"
