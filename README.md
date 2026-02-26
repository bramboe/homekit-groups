# HomeKit Entity Architect

A **Home Assistant Integration** that acts as a **Virtual Accessory Builder** for Apple Home (HomeKit). It lets you define a single “Functional Accessory” by assigning raw entities to **Service Slots**, then optionally **ghosts** (hides) those raw entities from your HomeKit Bridge so Apple Home shows one clean tile instead of many.

## What it does

- **Slot-based wrapper**: You pick a template (e.g. “Security Accessory” or “Garage Door”), assign entities to required/optional slots (actuator, state sensor, battery, obstruction), and the integration exposes **one** virtual entity that combines them.
- **State + command routing**: The virtual entity’s state comes from the “state” slot (e.g. door contact = locked/unlocked). Commands from HomeKit (lock/unlock, open/close) are sent to the “action” slot.
- **Ghosting**: Optionally, the integration updates your chosen HomeKit Bridge so that:
  - All raw slot entities are **excluded** from that bridge.
  - The new virtual Architect entity is **included**.
  - The bridge is reloaded so Apple Home updates immediately.

## Installation (Add-on repository)

1. In Home Assistant: **Settings** → **Add-ons** → **Add-on store** → **⋮** → **Repositories**.
2. Add this repository URL: **`https://github.com/bramboe/homekit-groups`**
3. Install the **HomeKit Entity Architect** add-on, then **Start** it.
4. **Restart Home Assistant** (Settings → System → Restart).
5. **Settings** → **Devices & services** → **Add integration** → search **HomeKit Entity Architect** and complete the setup.

*(Alternative: copy the `custom_components/homekit_architect` folder into your `config/custom_components/` directory, then restart and add the integration as above.)*

## Configuration Panel

After the integration is loaded, a **HomeKit Architect** item appears in the sidebar (or open **/config/homekit-architect**). The panel lets you:

- **Bridge selection** – Choose an active HomeKit Bridge from a dropdown (from the Config Entry registry).
- **Bridge Inspector** – See that bridge’s current include/exclude filter and a **live list of entities** exposed by it.
- **Search and domain filter** – Search bar and clickable domain chips to narrow the entity list.
- **Multi-select and “Package as Accessory”** – Select one or more entities, click **Package as Accessory**, then in the modal: set a display name, choose type (Smart Lock or Garage Door), assign entities to slots (with auto-suggested mapping), and optionally enable **“Hide source entities from HomeKit”** (ghosting). The integration creates the virtual entity and updates the bridge.

The panel talks to the integration via the WebSocket API (`homekit_architect/list_bridges`, `homekit_architect/bridge_entities`, `homekit_architect/package_accessory`). You can still add and manage accessories via **Settings → Devices & services → Add integration → HomeKit Entity Architect**.

## Setup flow (Add integration wizard)

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

## Development roadmap (all phases integrated)

| Phase | Description | Status |
|-------|-------------|--------|
| **1. Bridge Inspector** | UI to list active HomeKit bridges and their include/exclude filter | Done |
| **2. Multi-Select UI** | Entity list with search bar, domain toggles, and multi-select | Done |
| **3. Packaging Logic** | Backend creates virtual entities from selected entities + type + slot mapping | Done |
| **4. Auto-Exclusion** | “Ghost” method: update bridge exclude/include and reload | Done |

## Technical notes

- **Add-on interface:** The add-on follows patterns from [ESPHome](https://github.com/esphome/esphome) and [Matterbridge](https://github.com/Luligu/matterbridge-home-assistant-addon): `panel_title` and `panel_icon` for sidebar branding, `ingress_port` for the config server, and a `schema` + `options` so users get a proper **Configuration** tab (e.g. “Reinstall integration on start”). Translations in `translations/en.yaml` give friendly labels for schema options.
- **Versioning:** When releasing changes, bump the version in all three places: `custom_components/homekit_architect/manifest.json`, `homekit_architect/integration/homekit_architect/manifest.json`, and `homekit_architect/config.yaml` (add-on). Keep them in sync.
- The integration uses the same entity filter mechanism as the core HomeKit integration: it adds slot entity IDs to the bridge’s **exclude** list and the virtual Architect entity to the **include** list, then reloads the bridge.
- Virtual entities are registered with a stable `unique_id` so they survive renames in the entity registry.
- This repo is an **add-on repository**: the add-on installs the integration into your config; the integration runs inside Home Assistant and depends on the built-in **HomeKit** integration.

## Requirements

- Home Assistant with the **HomeKit** integration and at least one **HomeKit Bridge** (bridge mode) configured.
- Entities you assign to slots must already exist (locks, switches, binary sensors, covers, sensors, etc.).

## License

MIT (or your choice).
