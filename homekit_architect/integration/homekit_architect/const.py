"""Constants for HomeKit Entity Architect."""

from __future__ import annotations

DOMAIN = "homekit_architect"

# Config entry keys
CONF_TEMPLATE_ID = "template_id"
CONF_SLOTS = "slots"
CONF_HOMEKIT_BRIDGE_ENTRY_ID = "homekit_bridge_entry_id"
CONF_AUTOMATED_GHOSTING = "automated_ghosting"
CONF_ARCHITECT_ENTITY_FRIENDLY_NAME = "friendly_name"

# HomeKit bridge filter keys
CONF_FILTER = "filter"
CONF_INCLUDE_ENTITIES = "include_entities"
CONF_EXCLUDE_ENTITIES = "exclude_entities"
CONF_INCLUDE_DOMAINS = "include_domains"
CONF_EXCLUDE_DOMAINS = "exclude_domains"

# ── Slot keys ────────────────────────────────────────────────────────────
SLOT_ACTION = "action_slot"
SLOT_STATE = "state_slot"
SLOT_BATTERY = "battery_slot"
SLOT_OBSTRUCTION = "obstruction_slot"
SLOT_ACTUATOR = "actuator_slot"
SLOT_POSITION_SENSOR = "position_sensor_slot"
SLOT_SWITCH = "switch_slot"
SLOT_BRIGHTNESS = "brightness_slot"
SLOT_COLOR = "color_slot"
SLOT_SPEED = "speed_slot"
SLOT_CLIMATE = "climate_slot"
SLOT_TEMPERATURE_SENSOR = "temperature_sensor_slot"
SLOT_HUMIDITY_SENSOR = "humidity_sensor_slot"
SLOT_TARGET = "target_slot"
SLOT_MEDIA = "media_slot"
SLOT_POWER = "power_slot"
SLOT_POWER_SENSOR = "power_sensor_slot"
SLOT_VOLUME = "volume_slot"
SLOT_PRIMARY = "primary_slot"
SLOT_SECONDARY = "secondary_slot"
SLOT_POSITION = "position_slot"
SLOT_TILT = "tilt_slot"
SLOT_ARM = "arm_slot"
SLOT_TRIGGER = "trigger_slot"
SLOT_CAMERA = "camera_slot"
SLOT_MOTION = "motion_slot"
SLOT_AIR_QUALITY = "air_quality_slot"
SLOT_FILTER = "filter_slot"
SLOT_TIMER = "timer_slot"

# Combo templates: one accessory with multiple services (e.g. Fan + Light)
SLOT_FAN_SWITCH = "fan_switch_slot"
SLOT_LIGHT_SWITCH = "light_switch_slot"

# ── Template definitions ─────────────────────────────────────────────────
# Each template maps to one HA platform and defines required/optional slots.

TEMPLATES = {
    # ── Security & Access ────────────────────────────────────────────
    "lock": {
        "name": "Door Lock",
        "platform": "lock",
        "required_slots": [SLOT_ACTION, SLOT_STATE],
        "optional_slots": [SLOT_BATTERY, SLOT_OBSTRUCTION],
        "slot_labels": {
            SLOT_ACTION: "Lock actuator (switch or lock)",
            SLOT_STATE: "State sensor (door contact)",
            SLOT_BATTERY: "Battery (optional)",
            SLOT_OBSTRUCTION: "Obstruction sensor (optional)",
        },
    },
    "security_system": {
        "name": "Security System",
        "platform": "alarm_control_panel",
        "required_slots": [SLOT_ARM],
        "optional_slots": [SLOT_STATE, SLOT_BATTERY],
        "slot_labels": {
            SLOT_ARM: "Arm/Disarm control",
            SLOT_STATE: "State sensor (optional)",
            SLOT_BATTERY: "Battery (optional)",
        },
    },
    "doorbell": {
        "name": "Video Doorbell",
        "platform": "binary_sensor",
        "required_slots": [SLOT_TRIGGER],
        "optional_slots": [SLOT_CAMERA, SLOT_BATTERY],
        "slot_labels": {
            SLOT_TRIGGER: "Doorbell trigger",
            SLOT_CAMERA: "Camera stream (optional)",
            SLOT_BATTERY: "Battery (optional)",
        },
    },
    # ── Doors, Gates & Covers ────────────────────────────────────────
    "garage_door": {
        "name": "Garage Door",
        "platform": "cover",
        "required_slots": [SLOT_ACTUATOR, SLOT_POSITION_SENSOR],
        "optional_slots": [SLOT_OBSTRUCTION, SLOT_BATTERY],
        "slot_labels": {
            SLOT_ACTUATOR: "Open/Close actuator",
            SLOT_POSITION_SENSOR: "Position sensor",
            SLOT_OBSTRUCTION: "Obstruction sensor (optional)",
            SLOT_BATTERY: "Battery (optional)",
        },
    },
    "door": {
        "name": "Door",
        "platform": "cover",
        "required_slots": [SLOT_ACTUATOR, SLOT_POSITION_SENSOR],
        "optional_slots": [SLOT_BATTERY],
        "slot_labels": {
            SLOT_ACTUATOR: "Open/Close actuator",
            SLOT_POSITION_SENSOR: "Position sensor",
            SLOT_BATTERY: "Battery (optional)",
        },
    },
    "window": {
        "name": "Window",
        "platform": "cover",
        "required_slots": [SLOT_ACTUATOR, SLOT_POSITION_SENSOR],
        "optional_slots": [SLOT_BATTERY],
        "slot_labels": {
            SLOT_ACTUATOR: "Open/Close actuator",
            SLOT_POSITION_SENSOR: "Position sensor",
            SLOT_BATTERY: "Battery (optional)",
        },
    },
    "window_covering": {
        "name": "Window Covering",
        "platform": "cover",
        "required_slots": [SLOT_POSITION],
        "optional_slots": [SLOT_TILT, SLOT_BATTERY],
        "slot_labels": {
            SLOT_POSITION: "Position control",
            SLOT_TILT: "Tilt control (optional)",
            SLOT_BATTERY: "Battery (optional)",
        },
    },
    # ── Lighting & Power ─────────────────────────────────────────────
    "lightbulb": {
        "name": "Light",
        "platform": "light",
        "required_slots": [SLOT_SWITCH],
        "optional_slots": [SLOT_BRIGHTNESS, SLOT_COLOR],
        "slot_labels": {
            SLOT_SWITCH: "On/Off control",
            SLOT_BRIGHTNESS: "Brightness (optional)",
            SLOT_COLOR: "Color (optional)",
        },
    },
    "outlet": {
        "name": "Outlet",
        "platform": "switch",
        "required_slots": [SLOT_SWITCH],
        "optional_slots": [SLOT_POWER_SENSOR],
        "slot_labels": {
            SLOT_SWITCH: "On/Off control",
            SLOT_POWER_SENSOR: "Power sensor (optional)",
        },
    },
    "switch": {
        "name": "Switch",
        "platform": "switch",
        "required_slots": [SLOT_SWITCH],
        "optional_slots": [SLOT_STATE],
        "slot_labels": {
            SLOT_SWITCH: "On/Off control",
            SLOT_STATE: "State sensor (optional)",
        },
    },
    # ── Climate & Environment ────────────────────────────────────────
    "thermostat": {
        "name": "Thermostat",
        "platform": "climate",
        "required_slots": [SLOT_CLIMATE],
        "optional_slots": [SLOT_TEMPERATURE_SENSOR, SLOT_HUMIDITY_SENSOR],
        "slot_labels": {
            SLOT_CLIMATE: "Climate entity",
            SLOT_TEMPERATURE_SENSOR: "Temperature sensor (optional)",
            SLOT_HUMIDITY_SENSOR: "Humidity sensor (optional)",
        },
    },
    "fan": {
        "name": "Fan",
        "platform": "fan",
        "required_slots": [SLOT_SWITCH],
        "optional_slots": [SLOT_SPEED, SLOT_BATTERY],
        "slot_labels": {
            SLOT_SWITCH: "On/Off control",
            SLOT_SPEED: "Speed control (optional)",
            SLOT_BATTERY: "Battery (optional)",
        },
    },
    "fan_light": {
        "name": "Fan + Light",
        "platforms": ["fan", "light"],
        "required_slots": [SLOT_FAN_SWITCH, SLOT_LIGHT_SWITCH],
        "optional_slots": [],
        "slot_labels": {
            SLOT_FAN_SWITCH: "Fan on/off",
            SLOT_LIGHT_SWITCH: "Light on/off",
        },
        "platform_slots": {"fan": SLOT_FAN_SWITCH, "light": SLOT_LIGHT_SWITCH},
    },
    "air_purifier": {
        "name": "Air Purifier",
        "platform": "fan",
        "required_slots": [SLOT_SWITCH],
        "optional_slots": [SLOT_AIR_QUALITY, SLOT_FILTER],
        "slot_labels": {
            SLOT_SWITCH: "On/Off control",
            SLOT_AIR_QUALITY: "Air quality sensor (optional)",
            SLOT_FILTER: "Filter life (optional)",
        },
    },
    "humidifier": {
        "name": "Humidifier",
        "platform": "humidifier",
        "required_slots": [SLOT_SWITCH],
        "optional_slots": [SLOT_HUMIDITY_SENSOR, SLOT_TARGET],
        "slot_labels": {
            SLOT_SWITCH: "On/Off control",
            SLOT_HUMIDITY_SENSOR: "Humidity sensor (optional)",
            SLOT_TARGET: "Target humidity (optional)",
        },
    },
    "dehumidifier": {
        "name": "Dehumidifier",
        "platform": "humidifier",
        "required_slots": [SLOT_SWITCH],
        "optional_slots": [SLOT_HUMIDITY_SENSOR, SLOT_TARGET],
        "slot_labels": {
            SLOT_SWITCH: "On/Off control",
            SLOT_HUMIDITY_SENSOR: "Humidity sensor (optional)",
            SLOT_TARGET: "Target humidity (optional)",
        },
    },
    # ── Water ────────────────────────────────────────────────────────
    "sprinkler": {
        "name": "Sprinkler",
        "platform": "switch",
        "required_slots": [SLOT_SWITCH],
        "optional_slots": [SLOT_TIMER],
        "slot_labels": {
            SLOT_SWITCH: "On/Off control",
            SLOT_TIMER: "Timer / duration (optional)",
        },
    },
    "faucet": {
        "name": "Faucet",
        "platform": "switch",
        "required_slots": [SLOT_SWITCH],
        "optional_slots": [],
        "slot_labels": {SLOT_SWITCH: "On/Off control"},
    },
    "shower": {
        "name": "Shower Head",
        "platform": "switch",
        "required_slots": [SLOT_SWITCH],
        "optional_slots": [],
        "slot_labels": {SLOT_SWITCH: "On/Off control"},
    },
    # ── Media ────────────────────────────────────────────────────────
    "television": {
        "name": "Television",
        "platform": "media_player",
        "required_slots": [SLOT_MEDIA],
        "optional_slots": [SLOT_POWER],
        "slot_labels": {
            SLOT_MEDIA: "Media player entity",
            SLOT_POWER: "Power control (optional)",
        },
    },
    "speaker": {
        "name": "Speaker",
        "platform": "media_player",
        "required_slots": [SLOT_MEDIA],
        "optional_slots": [SLOT_VOLUME],
        "slot_labels": {
            SLOT_MEDIA: "Media player entity",
            SLOT_VOLUME: "Volume control (optional)",
        },
    },
    # ── Sensors ──────────────────────────────────────────────────────
    "sensor": {
        "name": "Sensor",
        "platform": "sensor",
        "required_slots": [SLOT_PRIMARY],
        "optional_slots": [SLOT_SECONDARY, SLOT_BATTERY],
        "slot_labels": {
            SLOT_PRIMARY: "Primary sensor",
            SLOT_SECONDARY: "Secondary sensor (optional)",
            SLOT_BATTERY: "Battery (optional)",
        },
    },
    # ── Other ────────────────────────────────────────────────────────
    "camera": {
        "name": "IP Camera",
        "platform": "camera",
        "required_slots": [SLOT_CAMERA],
        "optional_slots": [SLOT_MOTION],
        "slot_labels": {
            SLOT_CAMERA: "Camera entity",
            SLOT_MOTION: "Motion sensor (optional)",
        },
    },
    "programmable_switch": {
        "name": "Programmable Switch",
        "platform": "binary_sensor",
        "required_slots": [SLOT_TRIGGER],
        "optional_slots": [SLOT_BATTERY],
        "slot_labels": {
            SLOT_TRIGGER: "Trigger entity",
            SLOT_BATTERY: "Battery (optional)",
        },
    },
}
