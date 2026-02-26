# Changelog

All notable changes to this app are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.3.0] - 2026-02-26

### Changed

- **App UI redo (ingress):** The app now serves a real web UI at the ingress URL instead of redirecting. Opening "Open Web UI" shows the app dashboard immediately (no blank screen). The main action "Open HomeKit Architect panel" uses `target="_top"` so it opens the full panel in the same tab without duplicate sidebars.
- Aligned with [Home Assistant app tutorial](https://developers.home-assistant.io/docs/apps/tutorial/) and [presentation docs](https://developers.home-assistant.io/docs/apps/presentation/): serve content on port 8099, single HTML page with status, reinstall, and link to the integration panel.

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
