"""Sensor platform for Hydro-Québec integration."""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfEnergy, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.loader import async_get_integration

from .const import DOMAIN
from .coordinator import HydroQcConfigEntry, HydroQcDataCoordinator
from .entity import HydroQcSourceEntity, source_applies

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class HydroQcSensorEntityDescription(SensorEntityDescription):
    """Describe a Hydro-Québec sensor.

    ``data_source`` and the values of ``attributes`` are dotted paths in the coordinator's data, ``rates`` the rates the sensor exists for (``ALL`` for every rate).
    """

    data_source: str
    rates: tuple[str, ...]
    attributes: dict[str, str] | None = None


# Ported from hydroqc2mqtt
SENSORS: tuple[HydroQcSensorEntityDescription, ...] = (
    HydroQcSensorEntityDescription(
        key="balance",
        translation_key="balance",
        data_source="account.balance",
        rates=("ALL",),
        icon="mdi:currency-usd",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="CAD",
    ),
    HydroQcSensorEntityDescription(
        key="current_billing_period_current_day",
        translation_key="current_billing_period_current_day",
        data_source="contract.cp_current_day",
        rates=("ALL",),
        icon="mdi:calendar-start",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.DAYS,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HydroQcSensorEntityDescription(
        key="current_billing_period_duration",
        translation_key="current_billing_period_duration",
        data_source="contract.cp_duration",
        rates=("ALL",),
        icon="mdi:calendar-expand-horizontal",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.DAYS,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HydroQcSensorEntityDescription(
        key="current_billing_period_total_to_date",
        translation_key="current_billing_period_total_to_date",
        data_source="contract.cp_current_bill",
        rates=("ALL",),
        icon="mdi:currency-usd",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="CAD",
    ),
    HydroQcSensorEntityDescription(
        key="current_billing_period_projected_bill",
        translation_key="current_billing_period_projected_bill",
        data_source="contract.cp_projected_bill",
        rates=("ALL",),
        icon="mdi:currency-usd",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="CAD",
    ),
    HydroQcSensorEntityDescription(
        key="current_billing_period_daily_bill_mean",
        translation_key="current_billing_period_daily_bill_mean",
        data_source="contract.cp_daily_bill_mean",
        rates=("ALL",),
        icon="mdi:currency-usd",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="CAD",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HydroQcSensorEntityDescription(
        key="current_billing_period_daily_consumption_mean",
        translation_key="current_billing_period_daily_consumption_mean",
        data_source="contract.cp_daily_consumption_mean",
        rates=("ALL",),
        icon="mdi:home-lightning-bolt",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HydroQcSensorEntityDescription(
        key="current_billing_period_total_consumption",
        translation_key="current_billing_period_total_consumption",
        data_source="contract.cp_total_consumption",
        rates=("ALL",),
        icon="mdi:home-lightning-bolt",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    HydroQcSensorEntityDescription(
        key="current_billing_period_projected_total_consumption",
        translation_key="current_billing_period_projected_total_consumption",
        data_source="contract.cp_projected_total_consumption",
        rates=("ALL",),
        icon="mdi:home-lightning-bolt",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    HydroQcSensorEntityDescription(
        key="current_billing_period_average_temperature",
        translation_key="current_billing_period_average_temperature",
        data_source="contract.cp_average_temperature",
        rates=("ALL",),
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HydroQcSensorEntityDescription(
        key="current_billing_period_kwh_cost_mean",
        translation_key="current_billing_period_kwh_cost_mean",
        data_source="contract.cp_kwh_cost_mean",
        rates=("ALL",),
        icon="mdi:currency-usd",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="CAD/kWh",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HydroQcSensorEntityDescription(
        key="current_billing_period_rate",
        translation_key="current_billing_period_rate",
        data_source="contract.rate",
        rates=("ALL",),
        icon="mdi:playlist-check",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    HydroQcSensorEntityDescription(
        key="current_billing_period_rate_option",
        translation_key="current_billing_period_rate_option",
        data_source="contract.rate_option",
        rates=("ALL",),
        icon="mdi:playlist-star",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    HydroQcSensorEntityDescription(
        key="outage",
        translation_key="outage",
        data_source="contract.next_outage.start_date",
        rates=("ALL",),
        icon="mdi:calendar-start",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        attributes={
            "end_date": "contract.next_outage.end_date",
            "cause": "contract.next_outage.cause.name",
            "planned_duration": "contract.next_outage.planned_duration",
            "code": "contract.next_outage.code.name",
            "state": "contract.next_outage.status.name",
            "emergency_level": "contract.next_outage.emergency_level",
            "is_planned": "contract.next_outage.is_planned",
        },
    ),
    HydroQcSensorEntityDescription(
        key="current_billing_period_higher_price_consumption",
        translation_key="current_billing_period_higher_price_consumption",
        data_source="contract.cp_higher_price_consumption",
        rates=(
            "DT",
            "DPC",
        ),
        icon="mdi:home-lightning-bolt",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    HydroQcSensorEntityDescription(
        key="current_billing_period_lower_price_consumption",
        translation_key="current_billing_period_lower_price_consumption",
        data_source="contract.cp_lower_price_consumption",
        rates=(
            "DT",
            "DPC",
        ),
        icon="mdi:home-lightning-bolt-outline",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    HydroQcSensorEntityDescription(
        key="amount_saved_vs_base_rate",
        translation_key="amount_saved_vs_base_rate",
        data_source="contract.amount_saved_vs_base_rate",
        rates=(
            "DT",
            "DPC",
        ),
        icon="mdi:currency-usd",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="CAD",
    ),
    HydroQcSensorEntityDescription(
        key="dpc_state",
        translation_key="dpc_state",
        data_source="calendar_peak_handler.current_state",
        rates=("DPC",),
    ),
    HydroQcSensorEntityDescription(
        key="dpc_next_peak_start",
        translation_key="dpc_next_peak_start",
        data_source="calendar_peak_handler.next_peak.start_date",
        rates=("DPC",),
        icon="mdi:clock-start",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    HydroQcSensorEntityDescription(
        key="dpc_next_peak_end",
        translation_key="dpc_next_peak_end",
        data_source="calendar_peak_handler.next_peak.end_date",
        rates=("DPC",),
        icon="mdi:clock-end",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    HydroQcSensorEntityDescription(
        key="dpc_next_pre_heat_start",
        translation_key="dpc_next_pre_heat_start",
        data_source="calendar_peak_handler.next_peak.preheat.start_date",
        rates=("DPC",),
        icon="mdi:clock-start",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    HydroQcSensorEntityDescription(
        key="dpc_critical_hours_count",
        translation_key="dpc_critical_hours_count",
        data_source="contract.critical_called_hours",
        rates=("DPC",),
        icon="mdi:clock-alert-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        attributes={
            "max": "contract.max_critical_called_hours",
        },
    ),
    HydroQcSensorEntityDescription(
        key="dpc_winter_days_count",
        translation_key="dpc_winter_days_count",
        data_source="contract.winter_total_days_last_update",
        rates=("DPC",),
        icon="mdi:calendar-range-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        attributes={
            "max": "contract.winter_total_days",
        },
    ),
    HydroQcSensorEntityDescription(
        key="wc_state",
        translation_key="wc_state",
        data_source="calendar_peak_handler.current_state",
        rates=("DCPC",),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    HydroQcSensorEntityDescription(
        key="wc_cumulated_credit",
        translation_key="wc_cumulated_credit",
        data_source="contract.peak_handler.cumulated_credit",
        rates=("DCPC",),
        icon="mdi:currency-usd",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="CAD",
    ),
    HydroQcSensorEntityDescription(
        key="wc_projected_cumulated_credit",
        translation_key="wc_projected_cumulated_credit",
        data_source="contract.peak_handler.projected_cumulated_credit",
        rates=("DCPC",),
        icon="mdi:currency-usd",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="CAD",
    ),
    HydroQcSensorEntityDescription(
        key="wc_next_anchor_start",
        translation_key="wc_next_anchor_start",
        data_source="calendar_peak_handler.next_peak.anchor.start_date",
        rates=("DCPC",),
        icon="mdi:clock-start",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        attributes={
            "critical": "calendar_peak_handler.next_peak.is_critical",
        },
    ),
    HydroQcSensorEntityDescription(
        key="wc_next_anchor_end",
        translation_key="wc_next_anchor_end",
        data_source="calendar_peak_handler.next_peak.anchor.end_date",
        rates=("DCPC",),
        icon="mdi:clock-end",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        attributes={
            "critical": "calendar_peak_handler.next_peak.is_critical",
        },
    ),
    HydroQcSensorEntityDescription(
        key="wc_next_peak_start",
        translation_key="wc_next_peak_start",
        data_source="calendar_peak_handler.next_peak.start_date",
        rates=("DCPC",),
        icon="mdi:clock-start",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        attributes={
            "critical": "calendar_peak_handler.next_peak.is_critical",
        },
    ),
    HydroQcSensorEntityDescription(
        key="wc_next_peak_end",
        translation_key="wc_next_peak_end",
        data_source="calendar_peak_handler.next_peak.end_date",
        rates=("DCPC",),
        icon="mdi:clock-end",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        attributes={
            "critical": "calendar_peak_handler.next_peak.is_critical",
        },
    ),
    HydroQcSensorEntityDescription(
        key="wc_next_critical_peak_start",
        translation_key="wc_next_critical_peak_start",
        data_source="calendar_peak_handler.next_critical_peak.start_date",
        rates=("DCPC",),
        icon="mdi:clock-start",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    HydroQcSensorEntityDescription(
        key="wc_next_critical_peak_end",
        translation_key="wc_next_critical_peak_end",
        data_source="calendar_peak_handler.next_critical_peak.end_date",
        rates=("DCPC",),
        icon="mdi:clock-end",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    HydroQcSensorEntityDescription(
        key="wc_next_pre_heat_start",
        translation_key="wc_next_pre_heat_start",
        data_source="calendar_peak_handler.next_peak.preheat.start_date",
        rates=("DCPC",),
        icon="mdi:clock-start",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        attributes={
            "critical": "calendar_peak_handler.next_peak.is_critical",
        },
    ),
    HydroQcSensorEntityDescription(
        key="wc_yesterday_morning_peak_credit",
        translation_key="wc_yesterday_morning_peak_credit",
        data_source="contract.peak_handler.yesterday_morning_peak.credit",
        rates=("DCPC",),
        icon="mdi:currency-usd",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="CAD",
    ),
    HydroQcSensorEntityDescription(
        key="wc_yesterday_morning_peak_actual_consumption",
        translation_key="wc_yesterday_morning_peak_actual_consumption",
        data_source="contract.peak_handler.yesterday_morning_peak.actual_consumption",
        rates=("DCPC",),
        icon="mdi:home-lightning-bolt",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    HydroQcSensorEntityDescription(
        key="wc_yesterday_morning_peak_ref_consumption",
        translation_key="wc_yesterday_morning_peak_ref_consumption",
        data_source="contract.peak_handler.yesterday_morning_peak.ref_consumption",
        rates=("DCPC",),
        icon="mdi:home-lightning-bolt",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    HydroQcSensorEntityDescription(
        key="wc_yesterday_morning_peak_saved_consumption",
        translation_key="wc_yesterday_morning_peak_saved_consumption",
        data_source="contract.peak_handler.yesterday_morning_peak.saved_consumption",
        rates=("DCPC",),
        icon="mdi:home-lightning-bolt",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    HydroQcSensorEntityDescription(
        key="wc_yesterday_evening_peak_credit",
        translation_key="wc_yesterday_evening_peak_credit",
        data_source="contract.peak_handler.yesterday_evening_peak.credit",
        rates=("DCPC",),
        icon="mdi:currency-usd",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="CAD",
    ),
    HydroQcSensorEntityDescription(
        key="wc_yesterday_evening_peak_actual_consumption",
        translation_key="wc_yesterday_evening_peak_actual_consumption",
        data_source="contract.peak_handler.yesterday_evening_peak.actual_consumption",
        rates=("DCPC",),
        icon="mdi:home-lightning-bolt",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    HydroQcSensorEntityDescription(
        key="wc_yesterday_evening_peak_ref_consumption",
        translation_key="wc_yesterday_evening_peak_ref_consumption",
        data_source="contract.peak_handler.yesterday_evening_peak.ref_consumption",
        rates=("DCPC",),
        icon="mdi:home-lightning-bolt",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    HydroQcSensorEntityDescription(
        key="wc_yesterday_evening_peak_saved_consumption",
        translation_key="wc_yesterday_evening_peak_saved_consumption",
        data_source="contract.peak_handler.yesterday_evening_peak.saved_consumption",
        rates=("DCPC",),
        icon="mdi:home-lightning-bolt",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HydroQcConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hydro-Québec sensors from a config entry."""
    coordinator = entry.runtime_data

    integration = await async_get_integration(hass, DOMAIN)
    version = str(integration.version) if integration.version else "unknown"

    entities = [
        HydroQcSensor(coordinator, entry, description, version)
        for description in SENSORS
        if source_applies(coordinator, description)
    ]
    async_add_entities(entities)
    _LOGGER.debug("Added %d sensor entities", len(entities))


class HydroQcSensor(HydroQcSourceEntity, RestoreEntity, SensorEntity):
    """Representation of a Hydro-Québec sensor."""

    entity_description: HydroQcSensorEntityDescription

    def __init__(
        self,
        coordinator: HydroQcDataCoordinator,
        entry: HydroQcConfigEntry,
        description: HydroQcSensorEntityDescription,
        version: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, description, version)
        self.entity_description = description
        self._restored_value: Any = None

    async def async_added_to_hass(self) -> None:
        """Restore last state when entity is added to hass."""
        await super().async_added_to_hass()

        # Restore previous state to avoid showing unknown during reload
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                if last_state.state not in ("unknown", "unavailable"):
                    # For timestamp sensors, parse the ISO string back to datetime
                    if self.device_class == SensorDeviceClass.TIMESTAMP:
                        self._restored_value = datetime.datetime.fromisoformat(last_state.state)
                    else:
                        self._restored_value = last_state.state
            except (ValueError, TypeError):
                _LOGGER.debug(
                    "Could not restore sensor %s state: %s",
                    self.entity_id,
                    last_state.state,
                )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        # Check if sensor is seasonal and out of season
        if not self.coordinator.is_sensor_seasonal(self._data_source):
            return None

        value = self.coordinator.get_sensor_value(self._data_source)

        # Until the coordinator has data, show the value restored from the last run
        if value is None:
            return self._restored_value
        self._restored_value = None

        if isinstance(value, datetime.datetime):
            # A timestamp sensor takes the datetime itself
            if self.device_class == SensorDeviceClass.TIMESTAMP:
                return value
            return value.isoformat()

        if isinstance(value, datetime.timedelta):
            return f"{value.seconds / 60} minutes"

        if isinstance(value, (int, float)) and self.device_class == SensorDeviceClass.MONETARY:
            return round(value, 2)

        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return entity specific state attributes."""
        attributes: dict[str, Any] = {}

        for attr_key, attr_source in (self.entity_description.attributes or {}).items():
            attr_value = self.coordinator.get_sensor_value(attr_source)
            if attr_value is None:
                continue
            if isinstance(attr_value, datetime.datetime):
                attributes[attr_key] = attr_value.isoformat()
            elif isinstance(attr_value, datetime.timedelta):
                attributes[attr_key] = f"{attr_value.seconds / 60} minutes"
            else:
                attributes[attr_key] = attr_value

        attributes.update(self._source_attributes())
        return attributes
