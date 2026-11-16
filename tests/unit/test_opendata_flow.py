"""Unit tests for the OpenData steps of the config flow."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.hydroqc.const import (
    AUTH_MODE_OPENDATA,
    CONF_AUTH_MODE,
    CONF_CONTRACT_NAME,
    CONF_RATE,
    CONF_RATE_OPTION,
    DOMAIN,
)

FLOW = "custom_components.hydroqc.config_flow.base"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let the flow manager load the hydroqc custom integration."""


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Keep the entry created by the flow from setting up."""
    with patch("custom_components.hydroqc.async_setup_entry", return_value=True) as setup:
        yield setup


async def test_opendata_flow_creates_an_entry(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    """The sector and the rate are picked by key and stored as Hydro-Québec names them."""
    with (
        patch(f"{FLOW}.fetch_available_sectors", return_value=["Affaires", "Residentiel"]),
        patch(
            f"{FLOW}.fetch_offers_for_sector", return_value=[("M", "CPC"), ("M", "GDP")]
        ) as offers,
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_AUTH_MODE: AUTH_MODE_OPENDATA}
        )
        assert result["step_id"] == "opendata"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"sector": "affaires"}
        )
        assert result["step_id"] == "opendata_rate"
        offers.assert_awaited_once_with("Affaires")

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_CONTRACT_NAME: "Shop", "rate_selection": "m_gdp"}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Shop (MGDP)"
    assert result["data"][CONF_AUTH_MODE] == AUTH_MODE_OPENDATA
    assert result["data"][CONF_RATE] == "M"
    assert result["data"][CONF_RATE_OPTION] == "GDP"
