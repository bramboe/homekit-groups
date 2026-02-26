# Changelog

All notable changes to this app are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [2.0.0] - 2026-02-26

### Changed

- **Full UI in the app (ingress):** The app now serves the complete management interface directly. No more redirects or blank screens. "Open Web UI" shows the real UI with:
  - **Bridge selection** dropdown (auto-discovers HomeKit bridges from HA)
  - **Entity list** with live search bar, domain filter chips, and multi-select
  - **Package as Accessory** button and modal (display name, type, slot mapping, ghosting checkbox)
  - Install status, reinstall button, HA restart link
- Backend proxies calls to the HA REST API via the Supervisor (`homeassistant_api: true`) so the app can list bridges, entities, and create config entries without relying on the integration panel.
- Config flow walkthrough (template → slots → bridge → ghosting) is driven by the app server.
- Aligned with [HA app tutorial](https://developers.home-assistant.io/docs/apps/tutorial/) and [presentation docs](https://developers.home-assistant.io/docs/apps/presentation/): serve content on port 8099, single HTML page.

## [1.2.7] - 2026-02-26

### Added

- Panel title and icon, ingress port, schema options, translations.
- DOCS section on how to see updates (reload store, push to repo).

### Fixed

- Integration panel: added js_url, error handling, min-height.
- Ingress: relative URLs for status/reinstall so they work behind ingress path.

## [1.2.0] - 2026-02-25

### Added

- Add-on configuration page (ingress) with reinstall and link to integration panel.
- Python server for ingress; Dockerfile installs Python.

### Fixed

- Copy integration from `/usr/share/homekit_architect/` (not `/data`) so it works when Supervisor mounts `/data`.

## [1.1.0]

- Initial release: installs HomeKit Entity Architect integration into `custom_components`, supports Security Lock and Garage Door templates, bridge ghosting, config flow, and WebSocket API.
