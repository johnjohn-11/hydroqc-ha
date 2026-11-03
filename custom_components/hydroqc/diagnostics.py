"""Diagnostics support for Hydro-Québec integration.

Covers the Info-pannes tracking of an entry: coordinator health and the recent API payloads. The consumption location number is masked except for its last 4 digits, so a report with several locations stays readable.
"""

from __future__ import annotations

import copy
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import AUTH_MODE_INFO_PANNES, CONF_AUTH_MODE, DOMAIN
from .info_pannes.coordinator import InfoPannesCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Build a diagnostics report for a config entry."""
    if entry.data[CONF_AUTH_MODE] == AUTH_MODE_INFO_PANNES:
        info_pannes: InfoPannesCoordinator | None = entry.runtime_data
    else:
        info_pannes = hass.data[DOMAIN][entry.entry_id].info_pannes

    return {
        "entry": {
            "entry_id": entry.entry_id,
            "version": entry.version,
            "domain": entry.domain,
            "auth_mode": entry.data[CONF_AUTH_MODE],
            # User-chosen, so it can be a street address.
            "title": "**REDACTED**",
        },
        "info_pannes": _info_pannes_report(info_pannes) if info_pannes else None,
    }


def _info_pannes_report(coordinator: InfoPannesCoordinator) -> dict[str, Any]:
    return {
        "lieu_consommation": _mask(coordinator.lieu_conso),
        "last_update_success": coordinator.last_update_success,
        "update_interval": str(coordinator.update_interval),
        "api_compatible": coordinator.api_compatible,
        # Counters restart at zero with Home Assistant.
        "total_polls": coordinator.total_polls,
        "total_changes": coordinator.total_changes,
        "total_errors": coordinator.total_errors,
        "last_error": coordinator.last_error,
        "last_success_time": (
            coordinator.last_success_time.isoformat() if coordinator.last_success_time else None
        ),
        "current_data": _redact(coordinator.data) if coordinator.data else None,
        "api_history": [
            {"timestamp": snapshot["timestamp"], "data": _redact(snapshot["data"])}
            for snapshot in coordinator.api_history
        ],
    }


def _redact(data: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy of an API payload with ``idLieuConso`` masked."""
    redacted = copy.deepcopy(data)
    if "idLieuConso" in redacted:
        redacted["idLieuConso"] = _mask(str(redacted["idLieuConso"]))
    return redacted


def _mask(lieu: str) -> str:
    """Hide a consumption location number except for its last 4 digits."""
    return f"****{lieu[-4:]}" if len(lieu) > 4 else "****"
