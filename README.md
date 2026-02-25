# HomeKit Entity Architect

A **Home Assistant Integration** that acts as a **Virtual Accessory Builder** for Apple Home (HomeKit). It lets you define a single “Functional Accessory” by assigning raw entities to **Service Slots**, then optionally **ghosts** (hides) those raw entities from your HomeKit Bridge so Apple Home shows one clean tile instead of many.

## What it does

- **Slot-based wrapper**: You pick a template (e.g. “Security Accessory” or “Garage Door”), assign entities to required/optional slots (actuator, state sensor, battery, obstruction), and the integration exposes **one** virtual entity that combines them.
- **State + command routing**: The virtual entity’s state comes from the “state” slot (e.g. door contact = locked/unlocked). Commands from HomeKit (lock/unlock, open/close) are sent to the “action” slot.
- **Ghosting**: Optionally, the integration updates your chosen HomeKit Bridge so that:
  - All raw slot entities are **excluded** from that bridge.
  - The new virtual Architect entity is **included**.
  - The bridge is reloaded so Apple Home updates immediately.

## Installation

1. Copy the `custom_components/homekit_architect` folder into your Home Assistant `custom_components` directory (or add this repo as a custom repository and install via HACS if you later publish it).
2. Restart Home Assistant.
3. **Settings → Devices & Services → Add Integration** and search for **HomeKit Entity Architect**.

## Setup flow

1. **Template** – Choose the functional type (e.g. Security Accessory / Smart Lock, Garage Door).
2. **Slots** – Assign entities to each slot (e.g. lock actuator, door contact, battery sensor, obstruction sensor). Required slots must be filled.
3. **Bridge** – Select the existing HomeKit Bridge that should expose this accessory.
4. **Ghosting** – Turn “Automated ghosting” on to hide the raw entities on that bridge and show only the virtual one. Optionally set a friendly name.
5. Finish – The virtual entity is created and, if ghosting is on, the bridge filter is updated and reloaded.

## Templates

### Security Accessory (Smart Lock)

- **Action slot** (required): The switch or lock that actually moves the bolt.
- **State slot** (required): e.g. door contact sensor – closed = locked, open = unlocked.
- **Battery slot** (optional): Sensor for battery level (drives “Low Battery” in HomeKit).
- **Obstruction slot** (optional): Binary sensor for jammed lock.

### Garage Door Package

- **Actuator slot** (required): Cover or switch that opens/closes the door.
- **Position sensor slot** (required): Door contact or cover state for open/closed/opening/closing.
- **Battery slot** (optional): Battery sensor.

## Technical notes

- The integration uses the same entity filter mechanism as the core HomeKit integration: it adds slot entity IDs to the bridge’s **exclude** list and the virtual Architect entity to the **include** list, then reloads the bridge.
- Virtual entities are registered with a stable `unique_id` so they survive renames in the entity registry.
- This is a **Home Assistant integration** (custom component), not a HASS add-on or HACS-specific package; it runs inside Home Assistant and depends on the built-in **HomeKit** integration.

## Requirements

- Home Assistant with the **HomeKit** integration and at least one **HomeKit Bridge** (bridge mode) configured.
- Entities you assign to slots must already exist (locks, switches, binary sensors, covers, sensors, etc.).

## License

MIT (or your choice).
