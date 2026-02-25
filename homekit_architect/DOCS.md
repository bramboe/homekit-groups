# HomeKit Entity Architect (Add-on)

This add-on **installs** the HomeKit Entity Architect integration into your Home Assistant configuration. It does not run a separate service; it copies the integration files into `config/custom_components/homekit_architect/` so Home Assistant can load it.

## Installation

1. In Home Assistant: **Settings** → **Add-ons** → **Add-on store** → **⋮** (top right) → **Repositories**.
2. Add: `https://github.com/bramboe/homekit-groups`
3. Click **Add**, then **Close**.
4. Find **HomeKit Entity Architect** in the add-on list, click **Install**, then **Start**.
5. **Restart Home Assistant** (Settings → System → Restart).
6. Go to **Settings** → **Devices & services** → **Add integration** → search for **HomeKit Entity Architect** and complete the setup.

## What it does

When you **Start** the add-on, it installs the integration into your config folder and runs a small configuration server. After you restart Home Assistant, you can add the integration and create virtual accessories (e.g. Smart Lock, Garage Door) from slot entities and optionally hide the raw entities on your HomeKit Bridge (ghosting).

## Add-on configuration page (Web UI)

Open the add-on and click **Open Web UI** (or the add-on’s **Open** button when ingress is enabled). The configuration page lets you:

- **See status** – Whether the integration is installed and where.
- **Reinstall integration** – Copy the integration again into `custom_components` (e.g. after updating the add-on).
- **Open configuration panel** – Link to the main HomeKit Architect panel in Home Assistant (`/config/homekit-architect`) where you manage bridges and package accessories.

## Updating

Update the add-on from the Add-on store, then **Start** it again to overwrite the integration files. Restart Home Assistant to load the new version.

## Requirements

- Home Assistant OS or Supervised installation (so the add-on can access the config directory).
- An existing **HomeKit Bridge** (Settings → Devices & services → HomeKit → Add Bridge) before adding virtual accessories.
