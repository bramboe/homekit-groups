"""Virtual media_player platform for 'television' and 'speaker' templates.

Template pattern: state from slot entity (any domain); commands by slot domain.
Media_player entity: full state. Switch/light/fan: on = playing, off = off;
turn_on/turn_off, media_play -> turn_on, media_pause -> turn_off."""

from __future__ import annotations

from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerDeviceClass,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base import ArchitectBase, domain_of, slot_entity_is_on
from .const import SLOT_MEDIA, SLOT_POWER, SLOT_VOLUME

HANDLED_TEMPLATES = ("television", "speaker", "multi_service")


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    tid = entry.data.get("template_id")
    if tid not in HANDLED_TEMPLATES:
        return
    slots = entry.data.get("slots") or {}
    if tid == "multi_service":
        media_slots = [k for k, eid in slots.items() if eid and domain_of(eid) == "media_player"]
        if not media_slots:
            return
        async_add_entities([ArchitectMediaPlayer(hass, entry, "speaker", slot_key=sk) for sk in media_slots])
        return
    if not slots.get(SLOT_MEDIA):
        return
    async_add_entities([ArchitectMediaPlayer(hass, entry, tid)])


class ArchitectMediaPlayer(ArchitectBase, MediaPlayerEntity):

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        tid: str,
        slot_key: str | None = None,
    ) -> None:
        self._architect_init(hass, entry, "media_player", slot_key=slot_key)
        self._media_slot = slot_key if slot_key else SLOT_MEDIA
        self._attr_device_class = (
            MediaPlayerDeviceClass.TV if tid == "television"
            else MediaPlayerDeviceClass.SPEAKER
        )
        features = (
            MediaPlayerEntityFeature.TURN_ON
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.PAUSE
        )
        self._attr_supported_features = features

    @callback
    def _update_state(self) -> None:
        src = self._slot(self._media_slot)
        st = self.hass.states.get(src) if src else None
        dom = domain_of(src) if src else ""
        if dom == "media_player" and st and st.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                self._attr_state = MediaPlayerState(st.state)
            except ValueError:
                self._attr_state = MediaPlayerState.OFF
            attrs = st.attributes or {}
            self._attr_volume_level = attrs.get("volume_level")
            self._attr_is_volume_muted = attrs.get("is_volume_muted")
            self._attr_media_title = attrs.get("media_title")
        else:
            # Any other domain (switch, light, fan): on = playing, off = off
            is_on = slot_entity_is_on(self.hass, src) if src else None
            self._attr_state = MediaPlayerState.PLAYING if is_on else MediaPlayerState.OFF
            self._attr_volume_level = None
            self._attr_is_volume_muted = None
            self._attr_media_title = None
        self._attr_extra_state_attributes = {}

    async def async_added_to_hass(self) -> None:
        self._update_state()
        await self._async_track_slots(self._media_slot, SLOT_POWER, SLOT_VOLUME)

    async def async_turn_on(self) -> None:
        pwr = self._slot(SLOT_POWER) or self._slot(self._media_slot)
        await self._forward_service(pwr, "turn_on")

    async def async_turn_off(self) -> None:
        pwr = self._slot(SLOT_POWER) or self._slot(self._media_slot)
        await self._forward_service(pwr, "turn_off")

    async def async_media_play(self) -> None:
        eid = self._slot(self._media_slot)
        if domain_of(eid) == "media_player":
            await self._forward_service(eid, "media_play")
        else:
            await self._forward_service(eid, "turn_on")

    async def async_media_pause(self) -> None:
        eid = self._slot(self._media_slot)
        if domain_of(eid) == "media_player":
            await self._forward_service(eid, "media_pause")
        else:
            await self._forward_service(eid, "turn_off")

    async def async_set_volume_level(self, volume: float) -> None:
        vol_eid = self._slot(SLOT_VOLUME) or self._slot(self._media_slot)
        dom = domain_of(vol_eid)
        if dom == "media_player":
            await self._forward_service(vol_eid, "volume_set", {"volume_level": volume})
        elif dom in ("number", "input_number"):
            await self._forward_service(vol_eid, "set_value", {"value": volume * 100})
        # switch/light/fan: no volume; ignore
