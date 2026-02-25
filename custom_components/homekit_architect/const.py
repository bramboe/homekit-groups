"""Constants for the HomeKit Entity Architect integration."""

DOMAIN = "homekit_architect"

# Single app entry: entry.data["groups"] = list of accessory group dicts
CONF_GROUPS = "groups"
CONF_GROUP_ID = "id"

# Per-group keys (each group in CONF_GROUPS)
CONF_TARGET_DOMAIN = "target_domain"
CONF_MEMBER_ENTITIES = "member_entities"
CONF_BRIDGE_ID = "bridge_id"
CONF_APPLY_GHOST_HIDE = "apply_ghost_hide"
CONF_ENTITY_NAME = "entity_name"

# Target domain options (fan, climate, cover, lock)
TARGET_DOMAINS = ["fan"]

# Slot keys for entity mapping (type-specific; fan example)
FAN_SLOT_SPEED = "speed_entity"
FAN_SLOT_BATTERY = "battery_sensor"

HOMEKIT_DOMAIN = "homekit"
