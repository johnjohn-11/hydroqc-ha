"""Config flow steps of the Info-pannes mode: follow a location without an account.

The location is found from its civic number and postal code.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from pyhydropannes import (
    HydroPannesAmbiguousAddressError,
    HydroPannesClient,
    HydroPannesError,
    HydroPannesInvalidPostalCodeError,
    Location,
    normalize_postal_code,
)

from ..const import AUTH_MODE_INFO_PANNES, CONF_AUTH_MODE, CONF_LIEU_CONSO, DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_NOM_LIEU = "nom_lieu"
CONF_CODE_POSTAL = "code_postal"
CONF_NUMERO_CIVIQUE = "numero_civique"
CONF_APPARTEMENT = "appartement"

_NOM_SCHEMA = vol.All(str, vol.Strip, vol.Length(min=1))


class InfoPannesFlowMixin(config_entries.ConfigFlow):
    """Steps that set up a location followed on Info-pannes."""

    _info_pannes_lieux: dict[str, Location]
    _info_pannes_lieu: Location | None

    def _info_pannes_client(self) -> HydroPannesClient:
        # No retry while the user waits on the form: a failure is shown at once and the user can submit again.
        return HydroPannesClient(async_get_clientsession(self.hass), max_retries=0)

    async def async_step_info_pannes(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Look the location up from its civic number and postal code."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                lieux = await self._info_pannes_client().async_search_locations(
                    normalize_postal_code(user_input[CONF_CODE_POSTAL]),
                    user_input[CONF_NUMERO_CIVIQUE].strip(),
                    user_input.get(CONF_APPARTEMENT, "").strip(),
                )
            except HydroPannesInvalidPostalCodeError:
                errors = {CONF_CODE_POSTAL: "invalid_code_postal"}
            except HydroPannesAmbiguousAddressError:
                errors = {"base": "adresse_ambigue"}
            except HydroPannesError as err:
                _LOGGER.debug("Info-pannes address lookup error: %s", err)
                errors = {"base": "cannot_connect"}
            else:
                if not lieux:
                    errors = {"base": "adresse_introuvable"}
                elif len(lieux) == 1:
                    return await self._async_select_info_pannes_lieu(lieux[0])
                else:
                    self._info_pannes_lieux = {lieu.id: lieu for lieu in lieux}
                    return await self.async_step_info_pannes_choix()

        schema = vol.Schema(
            {
                vol.Required(CONF_NUMERO_CIVIQUE): str,
                vol.Required(CONF_CODE_POSTAL): str,
                vol.Optional(CONF_APPARTEMENT): str,
            }
        )
        return self.async_show_form(
            step_id="info_pannes",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
        )

    async def async_step_info_pannes_choix(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick one location when the address has several, such as apartments."""
        if user_input is not None:
            return await self._async_select_info_pannes_lieu(
                self._info_pannes_lieux[user_input[CONF_LIEU_CONSO]]
            )

        options = [
            SelectOptionDict(
                value=numero,
                label=f"{lieu.apartment_address or lieu.full_address or ''} ({numero})",
            )
            for numero, lieu in self._info_pannes_lieux.items()
        ]
        return self.async_show_form(
            step_id="info_pannes_choix",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LIEU_CONSO): SelectSelector(
                        SelectSelectorConfig(options=options, mode=SelectSelectorMode.LIST)
                    )
                }
            ),
        )

    async def _async_select_info_pannes_lieu(self, lieu: Location) -> ConfigFlowResult:
        """Claim the found number, aborting when it is already configured, then ask for a name."""
        await self.async_set_unique_id(f"info_pannes_{lieu.id}")
        if self.hass.config_entries.async_entry_for_domain_unique_id(
            DOMAIN, f"info_pannes_{lieu.id}"
        ):
            return self.async_abort(reason="lieu_deja_configure")
        # A portal contract already tracks its own location on Info-pannes.
        for coordinator in self.hass.data.get(DOMAIN, {}).values():
            info_pannes = getattr(coordinator, "info_pannes", None)
            if info_pannes and info_pannes.lieu_conso == lieu.id:
                return self.async_abort(reason="lieu_suivi_par_contrat")
        self._info_pannes_lieu = lieu
        return await self.async_step_info_pannes_nom()

    async def async_step_info_pannes_nom(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Name the location found by address, suggesting its street address."""
        lieu = self._info_pannes_lieu
        assert lieu is not None
        if user_input is not None:
            return self._async_create_info_pannes_entry(user_input[CONF_NOM_LIEU], lieu.id)

        return self.async_show_form(
            step_id="info_pannes_nom",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({vol.Required(CONF_NOM_LIEU): _NOM_SCHEMA}),
                {CONF_NOM_LIEU: lieu.street_address or ""},
            ),
            description_placeholders={
                "adresse": lieu.full_address or "",
                "lieu_consommation": lieu.id,
            },
        )

    def _async_create_info_pannes_entry(self, title: str, lieu: str) -> ConfigFlowResult:
        return self.async_create_entry(
            title=title,
            data={CONF_AUTH_MODE: AUTH_MODE_INFO_PANNES, CONF_LIEU_CONSO: lieu},
        )
