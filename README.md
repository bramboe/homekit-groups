# HomeKit Entity Architect

Group multiple Home Assistant entities into a single HomeKit-compatible accessory (e.g. Fan, Thermostat, Lock) and optionally hide the source entities from Apple Home (Ghost method).

## Features

- **Functional packaging** – Combine a light (dimmer), sensor, etc. into one virtual fan (or later: climate, lock) for HomeKit.
- **Ghost method** – Automatically update your HomeKit Bridge to exclude source entities and include the new virtual entity.
- **Live type-casting** – Map entities across domains (e.g. light → fan) with percentage/speed mapping.

## Installation

### HACS (recommended)

1. In HACS go to **Integrations** → **⋮** → **Custom repositories**.
2. Add: `https://github.com/bramboe/Homekit-Groups`  
   Type: **Integration**.
3. Restart Home Assistant, then **Settings** → **Devices & services** → **Add integration** → search for **HomeKit Entity Architect**.

### Manual

1. Copy the `custom_components/homekit_architect` folder into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Add the integration via **Settings** → **Devices & services** → **Add integration** → **HomeKit Entity Architect**.

## Requirements

- Home Assistant with the **HomeKit** integration.
- At least one **HomeKit Bridge** configured (needed for bridge selection and Ghost method).

## Configuration

1. Add the integration and run the wizard.
2. **Accessory type** – Choose e.g. Fan (more types in later versions).
3. **Entity mapping** – Name the virtual entity and pick the source entities (e.g. a light for speed, optional battery sensor).
4. **Bridge** – Select your HomeKit Bridge and enable **Apply Ghost Hide** to exclude source entities and show only the virtual one in Apple Home.

## Support

- [Documentation](https://github.com/bramboe/Homekit-Groups)
- [Issues](https://github.com/bramboe/Homekit-Groups/issues)
