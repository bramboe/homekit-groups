# HomeKit Entity Architect

A Home Assistant **custom integration** that acts as a **Virtual Accessory Builder**. You define a single “Functional Accessory” by assigning raw entities to **Service Slots**. The integration then exposes one virtual entity to Home Assistant (and thus to the HomeKit Bridge) and can **automatically hide** the raw slot entities from the selected HomeKit Bridge (“ghosting”) for a clean Apple Home experience.

## Features

- **Slot-based templates**: Choose a template (e.g. Security Lock, Garage Door) and assign your entities to required and optional slots.
- **Single virtual entity**: One lock or cover entity is created; state is derived from the State slot, commands are sent to the Action/Actuator slot.
- **Optional battery & obstruction**: Map battery and jammed/obstruction sensors so the virtual accessory can report low battery and obstruction to HomeKit.
- **Automated ghosting**: Optionally add all slot entity IDs to the chosen HomeKit Bridge’s **exclude** filter and reload the bridge so only the virtual accessory appears in Apple Home.

## Installation

1. Copy the `custom_components/homekit_architect` folder into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration** and search for **HomeKit Entity Architect**.

## Setup flow

1. **Template**: Select “Security Accessory (Smart Lock)” or “Garage Door Package”.
2. **Slots**: Assign entities to each slot (e.g. lock/switch for action, contact/lock for state; optional battery and obstruction sensors).
3. **Bridge**: Select the HomeKit Bridge that should expose this accessory, and enable “Automated ghosting” to hide the raw entities from that bridge.
4. **Name**: Give the virtual accessory a friendly name and finish.

After setup, the virtual entity is created and, if ghosting is enabled, the bridge’s entity filter is updated and reloaded so the raw entities are excluded and only the virtual one appears in HomeKit.

## Templates

| Template              | Platform | Required slots              | Optional slots   |
|-----------------------|----------|-----------------------------|------------------|
| Security Accessory    | Lock     | Action, State               | Battery, Obstruction |
| Garage Door Package   | Cover    | Actuator, Opening sensor    | Battery, Obstruction |

## Technical notes

- **Entity registry**: Slot assignments are stored by `entity_id`. If you rename an entity in the entity registry, update the Architect entry (reconfigure or remove and re-add) so the correct entity is used.
- **Ghosting**: The integration updates the HomeKit config entry’s **options** `filter.exclude_entities` and then reloads the bridge. Removing or disabling an Architect entry removes those entities from the exclude list and reloads the bridge again.
- **Platforms**: Lock entities are created for the Security Lock template; Cover entities for the Garage Door template. Each config entry forwards to exactly one platform.

## Requirements

- Home Assistant (tested on recent versions; uses standard config flow and entity patterns).
- An existing **HomeKit** integration (bridge) already set up if you want to use bridge selection and ghosting.

## License

MIT (or your chosen license).
