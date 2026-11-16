"""Binary sensor platform for Hydro-Québec integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.loader import async_get_integration

from .const import DOMAIN
from .coordinator import HydroQcConfigEntry, HydroQcDataCoordinator
from .entity import OPEN_DATA_SOURCE, HydroQcSourceEntity, source_applies

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class HydroQcBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe a Hydro-Québec binary sensor.

    ``data_source`` is a dotted path in the coordinator's data, ``rates`` the rates the sensor exists for (``ALL`` for every rate).
    """

    data_source: str
    rates: tuple[str, ...]


# Ported from hydroqc2mqtt
BINARY_SENSORS: tuple[HydroQcBinarySensorEntityDescription, ...] = (
    HydroQcBinarySensorEntityDescription(
        key="portal_status",
        translation_key="portal_status",
        data_source="portal_available",
        rates=("ALL",),
        icon="mdi:web-check",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    HydroQcBinarySensorEntityDescription(
        key="current_period_epp_enabled",
        translation_key="current_period_epp_enabled",
        data_source="contract.cp_epp_enabled",
        rates=("ALL",),
        icon="mdi:code-equal",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    HydroQcBinarySensorEntityDescription(
        key="wc_critical",
        translation_key="wc_critical",
        data_source="calendar_peak_handler.next_peak.is_critical",
        rates=("DCPC",),
        icon="mdi:flash-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HydroQcBinarySensorEntityDescription(
        key="wc_critical_peak_in_progress",
        translation_key="wc_critical_peak_in_progress",
        data_source="calendar_peak_handler.current_peak_is_critical",
        rates=("DCPC",),
        icon="mdi:flash-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HydroQcBinarySensorEntityDescription(
        key="wc_pre_heat",
        translation_key="wc_pre_heat",
        data_source="calendar_peak_handler.preheat_in_progress",
        rates=("DCPC",),
        icon="mdi:flash-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    HydroQcBinarySensorEntityDescription(
        key="wc_next_anchor_critical",
        translation_key="wc_next_anchor_critical",
        data_source="calendar_peak_handler.next_anchor.is_critical",
        rates=("DCPC",),
        icon="mdi:flash-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HydroQcBinarySensorEntityDescription(
        key="wc_next_peak_critical",
        translation_key="wc_next_peak_critical",
        data_source="calendar_peak_handler.next_peak.is_critical",
        rates=("DCPC",),
        icon="mdi:flash-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HydroQcBinarySensorEntityDescription(
        key="wc_upcoming_critical_peak",
        translation_key="wc_upcoming_critical_peak",
        data_source="calendar_peak_handler.is_any_critical_peak_coming",
        rates=("DCPC",),
        icon="mdi:flash-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HydroQcBinarySensorEntityDescription(
        key="wc_critical_morning_peak_today",
        translation_key="wc_critical_morning_peak_today",
        data_source="calendar_peak_handler.today_morning_peak.is_critical",
        rates=("DCPC",),
        icon="mdi:message-flash",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    HydroQcBinarySensorEntityDescription(
        key="wc_critical_evening_peak_today",
        translation_key="wc_critical_evening_peak_today",
        data_source="calendar_peak_handler.today_evening_peak.is_critical",
        rates=("DCPC",),
        icon="mdi:message-flash",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    HydroQcBinarySensorEntityDescription(
        key="wc_critical_morning_peak_tomorrow",
        translation_key="wc_critical_morning_peak_tomorrow",
        data_source="calendar_peak_handler.tomorrow_morning_peak.is_critical",
        rates=("DCPC",),
        icon="mdi:message-flash",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    HydroQcBinarySensorEntityDescription(
        key="wc_critical_evening_peak_tomorrow",
        translation_key="wc_critical_evening_peak_tomorrow",
        data_source="calendar_peak_handler.tomorrow_evening_peak.is_critical",
        rates=("DCPC",),
        icon="mdi:message-flash",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    HydroQcBinarySensorEntityDescription(
        key="dpc_pre_heat",
        translation_key="dpc_pre_heat",
        data_source="calendar_peak_handler.preheat_in_progress",
        rates=("DPC",),
        icon="mdi:flash-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    HydroQcBinarySensorEntityDescription(
        key="dpc_peak_in_progress",
        translation_key="dpc_peak_in_progress",
        data_source="calendar_peak_handler.peak_in_progress",
        rates=("DPC",),
        icon="mdi:flash-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HydroQcBinarySensorEntityDescription(
        key="dpc_critical_morning_peak_today",
        translation_key="dpc_critical_morning_peak_today",
        data_source="calendar_peak_handler.today_morning_peak.is_critical",
        rates=("DPC",),
        icon="mdi:message-flash",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    HydroQcBinarySensorEntityDescription(
        key="dpc_critical_evening_peak_today",
        translation_key="dpc_critical_evening_peak_today",
        data_source="calendar_peak_handler.today_evening_peak.is_critical",
        rates=("DPC",),
        icon="mdi:message-flash",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    HydroQcBinarySensorEntityDescription(
        key="dpc_critical_morning_peak_tomorrow",
        translation_key="dpc_critical_morning_peak_tomorrow",
        data_source="calendar_peak_handler.tomorrow_morning_peak.is_critical",
        rates=("DPC",),
        icon="mdi:message-flash",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    HydroQcBinarySensorEntityDescription(
        key="dpc_critical_evening_peak_tomorrow",
        translation_key="dpc_critical_evening_peak_tomorrow",
        data_source="calendar_peak_handler.tomorrow_evening_peak.is_critical",
        rates=("DPC",),
        icon="mdi:message-flash",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HydroQcConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hydro-Québec binary sensors from a config entry."""
    coordinator = entry.runtime_data

    integration = await async_get_integration(hass, DOMAIN)
    version = str(integration.version) if integration.version else "unknown"

    entities = [
        HydroQcBinarySensor(coordinator, entry, description, version)
        for description in BINARY_SENSORS
        if source_applies(coordinator, description)
    ]
    async_add_entities(entities)
    _LOGGER.debug("Added %d binary sensor entities", len(entities))


class HydroQcBinarySensor(HydroQcSourceEntity, RestoreEntity, BinarySensorEntity):
    """Representation of a Hydro-Québec binary sensor."""

    entity_description: HydroQcBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: HydroQcDataCoordinator,
        entry: HydroQcConfigEntry,
        description: HydroQcBinarySensorEntityDescription,
        version: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry, description, version)
        self.entity_description = description
        self._restored_state: bool | None = None

    async def async_added_to_hass(self) -> None:
        """Restore last state when entity is added to hass."""
        await super().async_added_to_hass()

        # Restore previous state to avoid switching off during reload
        if (last_state := await self.async_get_last_state()) is not None:
            self._restored_state = last_state.state == "on"

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        # Check if sensor is seasonal and out of season
        if not self.coordinator.is_sensor_seasonal(self._data_source):
            return None

        value = self.coordinator.get_sensor_value(self._data_source)

        if value is None:
            # Until the coordinator has data, show the state restored from the last run
            if self._restored_state is not None:
                return self._restored_state
            # Open data without a value means off-season, so no peak. Elsewhere the value is unknown.
            return False if self._data_source.startswith(OPEN_DATA_SOURCE) else None

        self._restored_state = None
        return bool(value)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return entity specific state attributes."""
        return self._source_attributes()

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # The portal status sensor reports the outage that makes the others unavailable
        return self._data_source == "portal_available" or super().available
