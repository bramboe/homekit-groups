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

## Safari: “Sheet constructor document doesn’t match adoptedStyleSheets”

On **Safari** (especially 26.x), opening the panel can trigger a frontend error from Home Assistant’s Lit-based UI. This comes from the HA frontend, not from this integration.

- **Workaround:** Use **Chrome** or **Firefox** to open the HomeKit Architect panel.
- If you enable **embed_iframe** (the integration does this by default), the panel may load in an iframe and avoid the issue on some setups.

## Troubleshooting: panel shows a blank screen

1. **Restart Home Assistant** after installing or updating the integration, then do a **hard refresh** in the browser (Ctrl+Shift+R or Cmd+Shift+R).
2. **Test if the panel script loads:** open  
   `http://YOUR_HA:8123/homekit_architect_panel/debug.html`  
   in your browser (replace YOUR_HA with your Home Assistant host, e.g. `homeassistant.local`).  
   - If you see "HomeKit Accessory Architect" and a bridge dropdown or an error message, the script works; the sidebar panel may be a cache or frontend issue.  
   - If that page is also blank or shows a 404, the integration may not be loaded: add it via **Settings** → **Devices & services** → **Add integration** → **HomeKit Entity Architect**, then restart HA.
3. Check the **browser console** (F12 → Console) on `/config/homekit-architect` for script or network errors.
4. In **Settings** → **System** → **Logs**, look for a line like `HomeKit Architect: registering panel; script at ...` to confirm the integration started.

## Requirements

- Home Assistant OS or Supervised installation (so the add-on can access the config directory).
- An existing **HomeKit Bridge** (Settings → Devices & services → HomeKit → Add Bridge) before adding virtual accessories.
