"""Base entity shared by every Info-pannes entity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION
from .coordinator import InfoPannesCoordinator

if TYPE_CHECKING:
    from asyncio import Handle

    from pyhydropannes import LocationState


class InfoPannesEntity(CoordinatorEntity[InfoPannesCoordinator]):
    """Wire an entity to its location's coordinator and device.

    Subclasses set ``_unique_id_suffix``. The suffixes come from the Hydro-Pannes integration and some differ from the translation key (``nbclient``, ``datefin``...).
    """

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    _unique_id_suffix: str
    # Set on the entities automations trigger on (Info-pannes, État du service, Intervention planifiée, the calendar), so an automation they start finds the detail sensors of the same poll already written.
    _write_after_details = False
    _deferred_write: Handle | None = None

    def __init__(self, coordinator: InfoPannesCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.unique_id_prefix}_{self._unique_id_suffix}"
        self._attr_device_info = coordinator.device_info

    @callback
    def _handle_coordinator_update(self) -> None:
        """Write the state, after the other entities of the poll for a summary entity.

        The coordinator calls every listener in turn within one loop iteration, so a write scheduled with call_soon runs once all of them have written, whatever order Home Assistant added the entities in.
        """
        if not self._write_after_details:
            super()._handle_coordinator_update()
            return
        if self._deferred_write is None:
            self._deferred_write = self.hass.loop.call_soon(self._write_deferred)

    @callback
    def _write_deferred(self) -> None:
        self._deferred_write = None
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Drop a write still scheduled for an entity being removed."""
        if self._deferred_write is not None:
            self._deferred_write.cancel()
            self._deferred_write = None
        await super().async_will_remove_from_hass()

    @property
    def _etat(self) -> LocationState:
        """Return the reading of the last successful payload, computed once per poll by the coordinator."""
        return self.coordinator.etat

    @property
    def _english(self) -> bool:
        """Return True when attribute texts should be in English.

        Home Assistant translates states and names but not attribute values, so the integration picks the French or English text itself from the configured language. French by default, also when the entity is not attached to Home Assistant.
        """
        hass = getattr(self, "hass", None)
        return hass is not None and not (hass.config.language or "fr").startswith("fr")

    @property
    def available(self) -> bool:
        """Return True only when the coordinator has successfully fetched data."""
        return super().available and self.coordinator.data is not None
