# HomeKit Entity Architect (Add-on)

This add-on **installs** the HomeKit Entity Architect integration into your Home Assistant configuration. It does not run a separate service; it copies the integration files into `config/custom_components/homekit_architect/` so Home Assistant can load it.

## Installation

1. In Home Assistant: **Settings** → **Add-ons** → **Add-on store** → **⋮** (top right) → **Repositories**.
2. Add: `https://github.com/bramboe/homekit-groups`
3. Click **Add**, then **Close**.
4. Find **HomeKit Entity Architect** in the add-on list, click **Install**, then **Start**.
5. **Restart Home Assistant once** (Settings → System → Restart, or use **Restart Home Assistant** in the add-on Web UI). Home Assistant only loads custom integrations at startup, so this one-time restart is required—same as for any custom integration.
6. Go to **Settings** → **Devices & services** → **Add integration** → search for **HomeKit Entity Architect** and complete the setup. You must add the integration at least once so the panel and WebSocket API are active (you can complete the flow without creating any accessories).

## What it does

When you **Start** the add-on, it installs the integration into your config folder and runs a small configuration server. After you restart Home Assistant, you can add the integration and create virtual accessories (e.g. Smart Lock, Garage Door) from slot entities and optionally hide the raw entities on your HomeKit Bridge (ghosting).

## Add-on Configuration tab

In **Settings → Apps → HomeKit Entity Architect → Configuration** you can set:

- **Reinstall integration on start** – When enabled (default), the integration is copied into `custom_components` every time the add-on starts. Turn this off if you only want to reinstall from the Web UI (e.g. to avoid overwriting local changes).

## Add-on Web UI

Open the add-on and click **Open Web UI** (or the **HomeKit Architect** sidebar icon). You see the app dashboard:

- **Open HomeKit Architect panel** – Opens the full panel in Home Assistant (bridge list, entity picker, Package as Accessory). Use this for day-to-day setup.
- **Install status** – Shows where the integration is installed.
- **Reinstall integration** – Copies the integration again (e.g. after an app update).
- **Restart Home Assistant** – Link to the server control page.

The app serves its own UI on the ingress port ([per the app tutorial](https://developers.home-assistant.io/docs/apps/tutorial/)); there is no redirect, so the screen is never blank.

## Updating

1. **Get the new version in Home Assistant** – The Supervisor fetches add-on versions from the GitHub repo. After you push a new release (e.g. bump `version` in `homekit_architect/config.yaml` and push to `main`), go to **Settings** → **Add-ons** (or **Apps**) → **Add-on store** → **⋮** (top right) → **Reload**. Then open **HomeKit Entity Architect** and click **Update** if it appears.
2. **Apply the update** – After updating the add-on, click **Start** (or restart the add-on) so it overwrites the integration files. Restart Home Assistant once to load the new integration code.

## Panel shows blank

If the HomeKit Architect panel is empty: (1) Make sure you have **added the integration** at least once (Settings → Devices & services → Add integration → HomeKit Entity Architect). (2) Restart Home Assistant after installing or updating the add-on. (3) Hard-refresh the frontend (Ctrl+Shift+R or clear frontend cache in Developer tools). (4) In the browser (F12 → Console), check for errors or a 404 on `/homekit_architect_panel/homekit-architect.js`.

## Requirements

- Home Assistant OS or Supervised installation (so the add-on can access the config directory).
- An existing **HomeKit Bridge** (Settings → Devices & services → HomeKit → Add Bridge) before adding virtual accessories.
