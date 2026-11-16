"""Unit tests for setup, options, service and removal behaviours."""

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hydroqc.const import CONF_PREHEAT_DURATION
from custom_components.hydroqc.coordinator import HydroQcDataCoordinator

BASE = "custom_components.hydroqc.coordinator.base"


async def test_preheat_duration_comes_from_the_options(
    hass: HomeAssistant, mock_config_entry_opendata: MockConfigEntry
) -> None:
    """The duration set in the options form wins over the one stored at setup."""
    mock_config_entry_opendata.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry_opendata, options={CONF_PREHEAT_DURATION: 60.0}
    )

    with patch(f"{BASE}.PublicDataClient") as public_client:
        coordinator = HydroQcDataCoordinator(hass, mock_config_entry_opendata)

    assert coordinator.preheat_duration == 60
    assert public_client.call_args.kwargs["preheat_duration"] == 60
