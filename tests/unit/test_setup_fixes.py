"""Unit tests for setup, options, service and removal behaviours."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hydroqc.button import _async_migrate_opendata_button
from custom_components.hydroqc.const import CONF_PREHEAT_DURATION, DOMAIN
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


async def test_opendata_refresh_succeeds_off_season(
    hass: HomeAssistant,
    mock_config_entry_opendata: MockConfigEntry,
    mock_public_client: MagicMock,
) -> None:
    """Off-season nothing is fetched, and the refresh still succeeds."""
    mock_config_entry_opendata.add_to_hass(hass)

    with (
        patch(f"{BASE}.PublicDataClient", return_value=mock_public_client),
        patch(f"{BASE}.is_winter_season", return_value=False),
    ):
        coordinator = HydroQcDataCoordinator(hass, mock_config_entry_opendata)
        await coordinator.async_refresh()

    assert coordinator.last_update_success
    mock_public_client.fetch_peak_data.assert_not_awaited()


async def test_consumption_sync_waits_for_the_first_refresh(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_webuser: MagicMock,
    mock_public_client: MagicMock,
) -> None:
    """The first refresh starts no consumption sync, the later ones do."""
    mock_config_entry.add_to_hass(hass)
    mock_webuser.check_hq_portal_status = AsyncMock(return_value=True)

    with (
        patch(f"{BASE}.WebUser", return_value=mock_webuser),
        patch(f"{BASE}.PublicDataClient", return_value=mock_public_client),
    ):
        coordinator = HydroQcDataCoordinator(hass, mock_config_entry)
        sync = AsyncMock()
        with patch.object(coordinator, "_async_regular_consumption_sync", sync):
            await coordinator.async_refresh()
            assert coordinator.last_update_success
            sync.assert_not_called()

            coordinator._first_refresh_done = True
            await coordinator.async_refresh()
            await asyncio.sleep(0)
            sync.assert_called_once()


async def test_opendata_button_leaves_the_unknown_contract_id(
    hass: HomeAssistant, mock_config_entry_opendata: MockConfigEntry
) -> None:
    """The button created under the "unknown" id moves to the entry's own id and its device is dropped."""
    entry = mock_config_entry_opendata
    entry.add_to_hass(hass)
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    device = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "unknown")}
    )
    ent_reg.async_get_or_create(
        "button", DOMAIN, "unknown_refresh_peak_data", config_entry=entry, device_id=device.id
    )

    _async_migrate_opendata_button(hass, entry)

    assert ent_reg.async_get_entity_id("button", DOMAIN, "unknown_refresh_peak_data") is None
    assert (
        ent_reg.async_get_entity_id("button", DOMAIN, f"{entry.entry_id}_refresh_peak_data")
        is not None
    )
    assert dev_reg.async_get_device(identifiers={(DOMAIN, "unknown")}) is None
