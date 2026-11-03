"""Calendar platform for Hydro-Québec integration: the planned interruptions of a location."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import AUTH_MODE_INFO_PANNES, CONF_AUTH_MODE, DOMAIN
from .coordinator import HydroQcDataCoordinator
from .info_pannes.calendar import info_pannes_calendars


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the planned-interruptions calendar of the entry's location, if it has one."""
    if entry.data[CONF_AUTH_MODE] == AUTH_MODE_INFO_PANNES:
        async_add_entities(info_pannes_calendars(entry.runtime_data))
        return
    coordinator: HydroQcDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    if coordinator.info_pannes:
        async_add_entities(info_pannes_calendars(coordinator.info_pannes))
