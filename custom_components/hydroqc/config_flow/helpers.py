"""Helper functions for Hydro-Québec config flow."""

from __future__ import annotations

import logging

import aiohttp

_LOGGER = logging.getLogger(__name__)

# Hydro-Québec open data API endpoint (Opendatasoft v2.1)
WINTER_PEAKS_API_BASE = "https://donnees.hydroquebec.com/api/explore/v2.1"
WINTER_PEAKS_DATASET = "evenements-pointe"
WINTER_PEAKS_URL = f"{WINTER_PEAKS_API_BASE}/catalog/datasets/{WINTER_PEAKS_DATASET}/records"

# Hydro-Québec offer codes and the (rate, rate option) pair each one stands for
RATE_CODE_MAPPING = {
    "CPC-D": ("D", "CPC"),
    "TPC-DPC": ("DPC", ""),
    "GDP-Affaires": ("M", "GDP"),
    "CPC-G": ("M", "CPC"),
    "TPC-GPC": ("M", "GPC"),
    "ENG01": ("M", "ENG"),
    "OEA": ("M", "OEA"),
}


def rate_key(rate: str, rate_option: str) -> str:
    """Return the key naming a rate in the form and in the translations, such as ``d_cpc``."""
    return f"{rate}_{rate_option}".lower().rstrip("_")


async def fetch_available_sectors() -> list[str]:
    """Fetch available sectors from Hydro-Québec open data API."""
    try:
        async with aiohttp.ClientSession() as session:
            params: dict[str, str | int] = {
                "select": "secteurclient",
                "limit": 100,
                "timezone": "America/Toronto",
            }
            async with session.get(
                WINTER_PEAKS_URL, params=params, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response.raise_for_status()
                data = await response.json()

                # Extract unique sectors from results
                results = data.get("results", [])
                sectors = {
                    record.get("secteurclient") for record in results if record.get("secteurclient")
                }

                return sorted(sectors)

    except Exception as err:
        _LOGGER.warning("Failed to fetch sectors from API: %s", err)
        return ["Residentiel", "Affaires"]


async def fetch_offers_for_sector(sector: str) -> list[tuple[str, str]]:
    """Fetch the (rate, rate option) pairs offered to a sector from Hydro-Québec open data API."""
    try:
        async with aiohttp.ClientSession() as session:
            params: dict[str, str | int] = {
                "select": "offre",
                "refine": f'secteurclient:"{sector}"',
                "limit": 100,
                "timezone": "America/Toronto",
            }
            async with session.get(
                WINTER_PEAKS_URL, params=params, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response.raise_for_status()
                data = await response.json()

                offers = {record.get("offre") for record in data.get("results", [])}
                return sorted(
                    RATE_CODE_MAPPING[offer] for offer in offers & RATE_CODE_MAPPING.keys()
                )

    except Exception as err:
        _LOGGER.warning("Failed to fetch offers for sector %s from API: %s", sector, err)
        if sector == "Residentiel":
            return [("D", "CPC"), ("DPC", "")]
        return [("M", "CPC"), ("M", "GDP")]
