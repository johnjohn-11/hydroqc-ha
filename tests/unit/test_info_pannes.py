"""Unit tests for the Info-pannes mode and the Info-pannes entities."""

from collections.abc import Generator
from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pyhydropannes import (
    HydroPannesAmbiguousAddressError,
    HydroPannesConnectionError,
    Location,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.hydroqc import (
    _async_contract_info_pannes,
    _async_remove_contract_info_pannes_entities,
)
from custom_components.hydroqc.const import (
    AUTH_MODE_INFO_PANNES,
    CONF_AUTH_MODE,
    CONF_LIEU_CONSO,
    DOMAIN,
)
from custom_components.hydroqc.diagnostics import async_get_config_entry_diagnostics

LIEU = "0000001234"
OTHER_LIEU = "0000005678"

ADDRESS_INPUT = {"numero_civique": "75", "code_postal": "h2z1a4"}

PAYLOAD: dict[str, Any] = {"etat": "A", "idLieuConso": LIEU, "interruptions": []}


def _location(lieu: str, apartment: str | None = None) -> Location:
    return Location(
        raw={},
        id=lieu,
        full_address="75, boulevard René-Lévesque Ouest, Montréal, Qc H2Z 1A4",
        street_address="75, boulevard René-Lévesque Ouest",
        apartment_address=apartment,
    )


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let the flow manager load the hydroqc custom integration."""


@pytest.fixture
def mock_search() -> Generator[AsyncMock]:
    """Mock the address lookup of the config flow."""
    with patch(
        "custom_components.hydroqc.config_flow.info_pannes.HydroPannesClient.async_search_locations",
    ) as search:
        yield search


@pytest.fixture
def mock_payload() -> Generator[AsyncMock]:
    """Mock the Info-pannes payload fetched by the coordinator."""
    with patch(
        "custom_components.hydroqc.info_pannes.coordinator.HydroPannesClient.async_get_payload",
        return_value=PAYLOAD,
    ) as get_payload:
        yield get_payload


@pytest.fixture
def info_pannes_entry() -> MockConfigEntry:
    """Return an Info-pannes config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Parents",
        data={CONF_AUTH_MODE: AUTH_MODE_INFO_PANNES, CONF_LIEU_CONSO: LIEU},
        unique_id=f"info_pannes_{LIEU}",
    )


async def _start_address_step(hass: HomeAssistant) -> dict:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_AUTH_MODE: AUTH_MODE_INFO_PANNES}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "info_pannes"
    return result


async def test_address_with_one_location_creates_entry(
    hass: HomeAssistant, mock_search: AsyncMock, mock_payload: AsyncMock
) -> None:
    """One location at the address goes straight to naming, then creates the entry."""
    mock_search.return_value = [_location(LIEU)]
    result = await _start_address_step(hass)

    result = await hass.config_entries.flow.async_configure(result["flow_id"], ADDRESS_INPUT)
    assert result["step_id"] == "info_pannes_nom"
    mock_search.assert_awaited_once_with("H2Z 1A4", "75", "")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"nom_lieu": " Parents "}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Parents"
    assert result["data"] == {CONF_AUTH_MODE: AUTH_MODE_INFO_PANNES, CONF_LIEU_CONSO: LIEU}
    assert result["result"].unique_id == f"info_pannes_{LIEU}"


async def test_address_with_several_locations_asks_which_one(
    hass: HomeAssistant, mock_search: AsyncMock, mock_payload: AsyncMock
) -> None:
    """Several locations at the address, such as apartments, go through a choice list."""
    mock_search.return_value = [_location(LIEU, "app. 1"), _location(OTHER_LIEU, "app. 2")]
    result = await _start_address_step(hass)

    result = await hass.config_entries.flow.async_configure(result["flow_id"], ADDRESS_INPUT)
    assert result["step_id"] == "info_pannes_choix"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_LIEU_CONSO: OTHER_LIEU}
    )
    assert result["step_id"] == "info_pannes_nom"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"nom_lieu": "App. 2"}
    )
    assert result["data"][CONF_LIEU_CONSO] == OTHER_LIEU


@pytest.mark.parametrize(
    ("search_result", "user_input", "errors"),
    [
        ([], ADDRESS_INPUT, {"base": "adresse_introuvable"}),
        (HydroPannesAmbiguousAddressError(), ADDRESS_INPUT, {"base": "adresse_ambigue"}),
        (HydroPannesConnectionError("down", attempts=1), ADDRESS_INPUT, {"base": "cannot_connect"}),
        ([], {**ADDRESS_INPUT, "code_postal": "123"}, {"code_postal": "invalid_code_postal"}),
    ],
)
async def test_address_errors(
    hass: HomeAssistant,
    mock_search: AsyncMock,
    search_result: Any,
    user_input: dict[str, str],
    errors: dict[str, str],
) -> None:
    """A lookup that finds nothing usable shows the form again with the error."""
    if isinstance(search_result, Exception):
        mock_search.side_effect = search_result
    else:
        mock_search.return_value = search_result
    result = await _start_address_step(hass)

    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "info_pannes"
    assert result["errors"] == errors


async def test_location_already_configured_aborts(
    hass: HomeAssistant, mock_search: AsyncMock, info_pannes_entry: MockConfigEntry
) -> None:
    """A location already followed by an Info-pannes entry is not added twice."""
    info_pannes_entry.add_to_hass(hass)
    mock_search.return_value = [_location(LIEU)]
    result = await _start_address_step(hass)

    result = await hass.config_entries.flow.async_configure(result["flow_id"], ADDRESS_INPUT)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "lieu_deja_configure"


async def test_location_of_a_portal_contract_aborts(
    hass: HomeAssistant, mock_search: AsyncMock
) -> None:
    """The location of a portal contract already has its Info-pannes entities."""
    contract = MagicMock()
    contract.info_pannes.lieu_conso = LIEU
    hass.data[DOMAIN] = {"portal_entry": contract}
    mock_search.return_value = [_location(LIEU)]
    result = await _start_address_step(hass)

    result = await hass.config_entries.flow.async_configure(result["flow_id"], ADDRESS_INPUT)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "lieu_suivi_par_contrat"


async def test_setup_creates_info_pannes_entities(
    hass: HomeAssistant, info_pannes_entry: MockConfigEntry, mock_payload: AsyncMock
) -> None:
    """An Info-pannes entry gets the outage entities, named after its device."""
    info_pannes_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(info_pannes_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)

    def state(domain: str, suffix: str) -> str:
        entity_id = ent_reg.async_get_entity_id(
            domain, DOMAIN, f"{info_pannes_entry.entry_id}_{suffix}"
        )
        assert entity_id is not None
        assert entity_id.startswith(f"{domain}.hydro_quebec_parents_")
        return hass.states.get(entity_id).state

    assert state("sensor", "info_pannes") == "aucune_panne"
    assert state("binary_sensor", "etat_service") == "off"
    assert state("calendar", "calendrier") == "off"

    def category(suffix: str) -> EntityCategory | None:
        entity_id = ent_reg.async_get_entity_id(
            "sensor", DOMAIN, f"{info_pannes_entry.entry_id}_{suffix}"
        )
        assert entity_id is not None
        return ent_reg.async_get(entity_id).entity_category

    assert category("info_pannes") is None
    assert category("cause") == EntityCategory.DIAGNOSTIC

    assert await hass.config_entries.async_unload(info_pannes_entry.entry_id)


async def test_contract_info_pannes_carries_the_full_device_info(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The contract's Info-pannes entities describe the whole contract device.

    The platforms set up in parallel, so the Info-pannes entities may be the ones that create the device.
    """
    coordinator = MagicMock(contract_id="contract123", rate_with_option="D")

    info_pannes = await _async_contract_info_pannes(hass, mock_config_entry, coordinator, LIEU)

    assert info_pannes.lieu_conso == LIEU
    assert info_pannes.unique_id_prefix == "contract123_info_pannes"
    device_info = info_pannes.device_info
    assert device_info["identifiers"] == {(DOMAIN, "contract123")}
    assert device_info["name"] == "Hydro-Québec - Home"
    assert device_info["manufacturer"] == "Hydro-Québec"
    assert device_info["model"] == "D"


async def test_disabled_option_removes_the_contract_info_pannes_entities(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Turning the option off removes the contract's Info-pannes entities and keeps the others."""
    mock_config_entry.add_to_hass(hass)
    ent_reg = er.async_get(hass)
    for unique_id in ("contract123_info_pannes_info_pannes", "contract123_balance"):
        ent_reg.async_get_or_create("sensor", DOMAIN, unique_id, config_entry=mock_config_entry)

    _async_remove_contract_info_pannes_entities(hass, mock_config_entry, "contract123")

    assert (
        ent_reg.async_get_entity_id("sensor", DOMAIN, "contract123_info_pannes_info_pannes") is None
    )
    assert ent_reg.async_get_entity_id("sensor", DOMAIN, "contract123_balance") is not None


async def test_refresh_data_service_refreshes_an_info_pannes_entry(
    hass: HomeAssistant, info_pannes_entry: MockConfigEntry, mock_payload: AsyncMock
) -> None:
    """The refresh_data service also reaches an Info-pannes entry."""
    info_pannes_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(info_pannes_entry.entry_id)
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{info_pannes_entry.entry_id}_info_pannes"
    )
    calls = mock_payload.await_count

    await hass.services.async_call(DOMAIN, "refresh_data", {"entity_id": entity_id}, blocking=True)
    await hass.async_block_till_done()

    assert mock_payload.await_count > calls
    assert await hass.config_entries.async_unload(info_pannes_entry.entry_id)


async def test_info_pannes_entry_has_no_options(
    hass: HomeAssistant, info_pannes_entry: MockConfigEntry
) -> None:
    """The portal and OpenData options do not apply to an Info-pannes entry."""
    info_pannes_entry.add_to_hass(hass)
    assert not info_pannes_entry.supports_options


async def test_diagnostics_mask_the_location(
    hass: HomeAssistant, info_pannes_entry: MockConfigEntry, mock_payload: AsyncMock
) -> None:
    """The report keeps only the last 4 digits of the location and hides the title."""
    info_pannes_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(info_pannes_entry.entry_id)
    await hass.async_block_till_done()

    report = await async_get_config_entry_diagnostics(hass, info_pannes_entry)

    assert report["entry"]["title"] == "**REDACTED**"
    assert report["info_pannes"]["lieu_consommation"] == "****1234"
    assert report["info_pannes"]["current_data"]["idLieuConso"] == "****1234"
    assert LIEU not in str(report)

    assert await hass.config_entries.async_unload(info_pannes_entry.entry_id)


async def test_first_polls_are_offset_by_a_random_delay(
    hass: HomeAssistant, info_pannes_entry: MockConfigEntry, mock_payload: AsyncMock
) -> None:
    """One extra refresh at a random delay shifts the cadence of each location."""
    info_pannes_entry.add_to_hass(hass)
    with patch("custom_components.hydroqc.info_pannes.coordinator.random.uniform", return_value=30):
        assert await hass.config_entries.async_setup(info_pannes_entry.entry_id)
        await hass.async_block_till_done()
    calls = mock_payload.await_count

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done()

    assert mock_payload.await_count == calls + 1
    assert await hass.config_entries.async_unload(info_pannes_entry.entry_id)
