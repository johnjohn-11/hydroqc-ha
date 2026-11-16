"""Base entities shared by the Hydro-Québec platforms."""

from __future__ import annotations

from typing import Any, Protocol

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_CONTRACT_ID, CONF_CONTRACT_NAME, DOMAIN
from .coordinator import HydroQcConfigEntry, HydroQcDataCoordinator

CALENDAR_SOURCE = "calendar_peak_handler."
OPEN_DATA_SOURCE = "public_client."


class SourceDescription(Protocol):
    """What the sensor and binary sensor descriptions have in common."""

    @property
    def key(self) -> str:
        """Return the key of the entity."""

    @property
    def data_source(self) -> str:
        """Return the dotted path of the value in the coordinator's data."""

    @property
    def rates(self) -> tuple[str, ...]:
        """Return the rates the entity exists for, or ``ALL``."""


def source_applies(coordinator: HydroQcDataCoordinator, description: SourceDescription) -> bool:
    """Tell whether an entity exists for the entry's rate, mode and calendar."""
    if "ALL" not in description.rates and coordinator.rate_with_option not in description.rates:
        return False

    source = description.data_source
    # Without an account only the open data is available
    if coordinator.is_opendata_mode and not source.startswith(OPEN_DATA_SOURCE):
        return False

    # The contract's own peak handler only exists for winter credits
    if "contract.peak_handler." in source and coordinator.rate_option != "CPC":
        return False

    return not source.startswith(CALENDAR_SOURCE) or bool(coordinator.calendar_peak_handler)


class HydroQcEntity(CoordinatorEntity[HydroQcDataCoordinator]):
    """Wire an entity to its coordinator and to the device of its contract."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HydroQcDataCoordinator,
        entry: HydroQcConfigEntry,
        key: str,
        version: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        # An OpenData entry has no contract id: its entry id stands for it
        contract_id = str(entry.data.get(CONF_CONTRACT_ID, entry.entry_id))
        self._attr_unique_id = f"{contract_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, contract_id)},
            name=f"Hydro-Québec - {entry.data.get(CONF_CONTRACT_NAME, 'OpenData')}",
            manufacturer="Hydro-Québec",
            model=coordinator.rate_with_option,
            sw_version=version,
        )


class HydroQcSourceEntity(HydroQcEntity):
    """An entity whose value is read from one data source of the coordinator."""

    # They change on every update or never: not worth a row in the recorder
    _unrecorded_attributes = frozenset({"last_update", "data_source"})

    def __init__(
        self,
        coordinator: HydroQcDataCoordinator,
        entry: HydroQcConfigEntry,
        description: SourceDescription,
        version: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, entry, description.key, version)
        self._data_source = description.data_source

        if self._data_source.startswith(CALENDAR_SOURCE):
            # Set in the attributes: the calendar's name is not known yet
            self._attr_attribution = None
        elif self._data_source.startswith(OPEN_DATA_SOURCE):
            self._attr_attribution = "Données ouvertes Hydro-Québec"
        elif coordinator.is_portal_mode:
            self._attr_attribution = "Espace Client Hydro-Québec"

    def _source_attributes(self) -> dict[str, Any]:
        """Return the attributes telling where and when the value comes from."""
        attributes: dict[str, Any] = {}
        if self.coordinator.last_update_success_time:
            attributes["last_update"] = self.coordinator.last_update_success_time.isoformat()

        if self._data_source.startswith(CALENDAR_SOURCE):
            attributes["data_source"] = "calendar"
            handler = self.coordinator.calendar_peak_handler
            if handler and handler.calendar_name:
                attributes["attribution"] = f"Calendrier {handler.calendar_name}"
        elif self._data_source.startswith(OPEN_DATA_SOURCE):
            attributes["data_source"] = "open_data"
        elif self.coordinator.is_portal_mode:
            attributes["data_source"] = "portal"
        else:
            attributes["data_source"] = "unknown"
        return attributes
