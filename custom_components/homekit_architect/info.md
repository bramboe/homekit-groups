# HomeKit Entity Architect

Group multiple entities into a single HomeKit accessory and optionally hide the originals in Apple Home.

## Installation

Add this repository as a [custom repository](https://hacs.xyz/docs/configuration/config_entry/) in HACS (Integration), then install **HomeKit Entity Architect**. Restart Home Assistant and add the integration via **Settings** → **Devices & services** → **Add integration**.

## Setup

You need at least one **HomeKit Bridge** (HomeKit integration). In the config flow you will:

1. Choose the accessory type (e.g. Fan).
2. Map source entities (e.g. a light for speed, optional battery sensor).
3. Select the bridge and enable **Apply Ghost Hide** to exclude source entities from HomeKit and expose only the new virtual entity.
