# HomeKit Entity Architect (Add-on)

This add-on **installs** the HomeKit Entity Architect integration into your Home Assistant configuration. It does not run a separate service; it copies the integration files into `config/custom_components/homekit_architect/` so Home Assistant can load it.

## Installation

1. In Home Assistant: **Settings** → **Add-ons** → **Add-on store** → **⋮** (top right) → **Repositories**.
2. Add: `https://github.com/bramboe/homekit-groups`
3. Click **Add**, then **Close**.
4. Find **HomeKit Entity Architect** in the add-on list, click **Install**, then **Start**.
5. **Restart Home Assistant** (Settings → System → Restart).
6. Go to **Settings** → **Devices & services** → **Add integration** → search for **HomeKit Entity Architect** and complete the setup.

## Configuration screen

The add-on’s **Configuration** tab has no options (by design). To configure devices and package entities into accessories:

- **Open Web UI** on the add-on’s **Info** tab should take you to the HomeKit Architect panel. If it only opens the main Home Assistant screen, use the sidebar instead.
- **Sidebar:** open **Settings** (or **Developer tools**) and click **HomeKit Architect** in the sidebar, or go directly to **Settings** → **Devices & services** → **Integrations** and open **HomeKit Entity Architect**.

## What it does

When you **Start** the add-on, it writes the integration into your config folder. After you restart Home Assistant, you can add the integration and create virtual accessories (e.g. Smart Lock, Garage Door) from slot entities and optionally hide the raw entities on your HomeKit Bridge (ghosting).

## Updating

Update the add-on from the Add-on store, then **Start** it again to overwrite the integration files. Restart Home Assistant to load the new version.

## Requirements

- Home Assistant OS or Supervised installation (so the add-on can access the config directory).
- An existing **HomeKit Bridge** (Settings → Devices & services → HomeKit → Add Bridge) before adding virtual accessories.
