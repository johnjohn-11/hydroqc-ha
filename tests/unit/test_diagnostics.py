"""Unit tests for the diagnostics report."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hydroqc.coordinator import HydroQcDataCoordinator
from custom_components.hydroqc.diagnostics import async_get_config_entry_diagnostics

BASE = "custom_components.hydroqc.coordinator.base"


async def test_diagnostics_hide_the_account(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_webuser: MagicMock,
    mock_public_client: MagicMock,
) -> None:
    """The report tells the coordinator's state and none of the account's identifiers."""
    mock_config_entry.add_to_hass(hass)
    mock_webuser.check_hq_portal_status = AsyncMock(return_value=True)
    with (
        patch(f"{BASE}.WebUser", return_value=mock_webuser),
        patch(f"{BASE}.PublicDataClient", return_value=mock_public_client),
    ):
        coordinator = HydroQcDataCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()
    mock_config_entry.runtime_data = coordinator

    report = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert report["coordinator"]["last_update_success"] is True
    assert report["coordinator"]["portal_mode"] is True
    assert report["coordinator"]["portal_available"] is True
    dumped = json.dumps(report, default=str)
    for key in ("username", "password", "contract_id", "customer_id", "account_id"):
        assert str(mock_config_entry.data[key]) not in dumped
