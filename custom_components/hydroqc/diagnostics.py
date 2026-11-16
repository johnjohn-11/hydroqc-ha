"""Diagnostics support for Hydro-Québec integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import CONF_ACCOUNT_ID, CONF_CONTRACT_ID, CONF_CONTRACT_NAME, CONF_CUSTOMER_ID
from .coordinator import HydroQcConfigEntry

# The title and the unique id are built from the contract name and the contract id
TO_REDACT = {
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_CUSTOMER_ID,
    CONF_ACCOUNT_ID,
    CONF_CONTRACT_ID,
    CONF_CONTRACT_NAME,
    "title",
    "unique_id",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,  # noqa: ARG001
    entry: HydroQcConfigEntry,
) -> dict[str, Any]:
    """Build a diagnostics report for a config entry."""
    coordinator = entry.runtime_data
    peak_handler = coordinator.public_client.peak_handler
    last_update = coordinator.last_update_success_time

    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "coordinator": {
            "rate": coordinator.rate_with_option,
            "portal_mode": coordinator.is_portal_mode,
            "last_update_success": coordinator.last_update_success,
            "last_update_success_time": last_update.isoformat() if last_update else None,
            "portal_available": coordinator.portal_available,
            "reauth_required": coordinator.reauth_required,
            "periods_unavailable": coordinator.periods_unavailable,
            "calendar_configured": coordinator.calendar_peak_handler is not None,
            "consumption_history_syncing": coordinator.is_consumption_history_syncing,
        },
        "open_data_peak_events": [
            {
                "start": event.start_date.isoformat(),
                "end": event.end_date.isoformat(),
                "is_critical": event.is_critical,
            }
            for event in (peak_handler._events if peak_handler else [])
        ],
    }
