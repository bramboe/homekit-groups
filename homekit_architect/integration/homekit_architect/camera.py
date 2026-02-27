"""Virtual camera platform for the 'camera' template (proxies a camera entity)."""

from __future__ import annotations

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base import ArchitectBase
from .const import SLOT_CAMERA, SLOT_MOTION

HANDLED_TEMPLATES = ("camera",)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    tid = entry.data.get("template_id")
    if tid not in HANDLED_TEMPLATES:
        return
    slots = entry.data.get("slots") or {}
    if not slots.get(SLOT_CAMERA):
        return
    async_add_entities([ArchitectCamera(hass, entry)])


class ArchitectCamera(ArchitectBase, Camera):

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        Camera.__init__(self)
        self._architect_init(hass, entry, "camera")

    @callback
    def _update_state(self) -> None:
        src = self._slot(SLOT_CAMERA)
        st = self.hass.states.get(src) if src else None
        if st and st.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self._attr_is_streaming = st.state == "streaming"
            self._attr_is_on = st.state != "off"
        else:
            self._attr_is_on = False

        attrs: dict = {}
        mot = self._slot(SLOT_MOTION)
        if mot:
            ms = self.hass.states.get(mot)
            if ms:
                attrs["motion_detected"] = ms.state == "on"
        self._attr_extra_state_attributes = attrs

    async def async_added_to_hass(self) -> None:
        self._update_state()
        await self._async_track_slots(SLOT_CAMERA, SLOT_MOTION)

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Forward image request to the source camera."""
        src = self._slot(SLOT_CAMERA)
        if not src:
            return None
        cam = self.hass.states.get(src)
        if not cam:
            return None
        from homeassistant.components.camera import async_get_image
        try:
            img = await async_get_image(self.hass, src, width=width, height=height)
            return img.content
        except Exception:
            return None
