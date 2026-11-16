"""Button platform for Hydro-Québec integration."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.loader import async_get_integration

from .const import CONF_CONTRACT_ID, CONF_CONTRACT_NAME, DOMAIN
from .coordinator import HydroQcConfigEntry, HydroQcDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HydroQcConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hydro-Québec button entities from a config entry."""
    coordinator = entry.runtime_data

    # Get integration version from manifest
    integration = await async_get_integration(hass, DOMAIN)
    version = str(integration.version) if integration.version else "unknown"

    if CONF_CONTRACT_ID not in entry.data:
        _async_migrate_opendata_button(hass, entry)

    entities: list[ButtonEntity] = []

    # Only add refresh button for DPC/DCPC rates with calendar configured
    if coordinator.rate_with_option in ["DPC", "DCPC"] and coordinator.calendar_peak_handler:
        entities.append(HydroQcRefreshPeakDataButton(coordinator, entry, version))

    if entities:
        async_add_entities(entities)
        _LOGGER.debug("Added %d button entities", len(entities))


@callback
def _async_migrate_opendata_button(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Move an OpenData entry's button off the "unknown" contract id it was created with.

    Every OpenData entry used that same id, for the button's unique id and for a device of its own.
    """
    ent_reg = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        if entity.domain == "button" and entity.unique_id == "unknown_refresh_peak_data":
            # Detached first: removing a device removes the entities still attached to it
            ent_reg.async_update_entity(
                entity.entity_id,
                new_unique_id=f"{entry.entry_id}_refresh_peak_data",
                device_id=None,
            )

    dev_reg = dr.async_get(hass)
    if device := dev_reg.async_get_device(identifiers={(DOMAIN, "unknown")}):
        dev_reg.async_update_device(device.id, remove_config_entry_id=entry.entry_id)


class HydroQcRefreshPeakDataButton(CoordinatorEntity[HydroQcDataCoordinator], ButtonEntity):
    """Button to manually refresh peak data from OpenData and calendar."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:refresh"

    def __init__(
        self,
        coordinator: HydroQcDataCoordinator,
        entry: ConfigEntry,
        version: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._entry = entry
        self._version = version

        # Same fallback as the sensors, so an OpenData entry's button joins their device
        contract_id = entry.data.get(CONF_CONTRACT_ID, entry.entry_id)
        contract_name = entry.data.get(CONF_CONTRACT_NAME, "OpenData")

        self._attr_unique_id = f"{contract_id}_refresh_peak_data"
        self._attr_translation_key = "refresh_peak_data"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(contract_id))},
            name=f"Hydro-Québec - {contract_name}",
            manufacturer="Hydro-Québec",
            model=coordinator.rate_with_option,
            sw_version=version,
        )

    async def async_press(self) -> None:
        """Handle button press - refresh OpenData and Calendar data.

        This does NOT refresh Portal data (contract/billing).
        Only refreshes peak announcement data and calendar-based sensor data.
        """
        _LOGGER.info("[Button] Manual refresh triggered for %s", self.coordinator.contract_name)

        # Refresh OpenData (peak announcements)
        if self.coordinator.public_client:
            try:
                _LOGGER.debug("[Button] Fetching OpenData peak data")
                await self.coordinator.public_client.fetch_peak_data()
                _LOGGER.debug("[Button] OpenData peak data fetched successfully")

                # Sync to calendar if events changed (signature-based detection)
                if (
                    self.coordinator._calendar_entity_id
                    and self.coordinator.public_client.peak_handler
                ):
                    current_signature = self.coordinator._get_critical_events_signature()
                    if current_signature != self.coordinator._last_critical_events_signature:
                        if (
                            self.coordinator._calendar_sync_task is None
                            or self.coordinator._calendar_sync_task.done()
                        ):
                            self.coordinator._calendar_sync_task = asyncio.create_task(
                                self.coordinator._async_sync_calendar_events()
                            )
                            self.coordinator._last_critical_events_signature = current_signature
                            _LOGGER.debug(
                                "[Button] Calendar sync triggered (signature changed)",
                            )

            except Exception as err:
                _LOGGER.warning("[Button] Failed to fetch OpenData peak data: %s", err)

        # Wait for calendar sync to complete before reading calendar
        if self.coordinator._calendar_sync_task and not self.coordinator._calendar_sync_task.done():
            try:
                _LOGGER.debug("[Button] Waiting for calendar sync to complete")
                await asyncio.wait_for(self.coordinator._calendar_sync_task, timeout=30.0)
            except TimeoutError:
                _LOGGER.warning("[Button] Calendar sync timed out, proceeding anyway")
            except Exception as err:
                _LOGGER.warning("[Button] Calendar sync failed: %s, proceeding anyway", err)

        # Refresh calendar-based sensor data
        if self.coordinator.calendar_peak_handler:
            _LOGGER.debug("[Button] Refreshing calendar peak data")
            await self.coordinator.async_load_calendar_peak_events()

        # Notify listeners of updated data
        self.coordinator.async_set_updated_data(self.coordinator.data)
        _LOGGER.info("[Button] Peak data refresh complete for %s", self.coordinator.contract_name)
