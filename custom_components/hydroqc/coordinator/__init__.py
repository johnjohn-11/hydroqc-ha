"""Coordinator package for Hydro-Québec integration."""

# Re-export dependencies for backward compatibility (used by tests)
from hydroqc.webuser import WebUser

from .. import calendar_manager
from ..public_data_client import PublicDataClient
from .base import HydroQcConfigEntry, HydroQcDataCoordinator

__all__ = [
    "HydroQcConfigEntry",
    "HydroQcDataCoordinator",
    "PublicDataClient",
    "WebUser",
    "calendar_manager",
]
