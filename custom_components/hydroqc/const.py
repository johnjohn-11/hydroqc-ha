"""Constants for the Hydro-Québec integration."""

from typing import Final

DOMAIN: Final = "hydroqc"

# Config flow constants
CONF_CONTRACT_ID: Final = "contract_id"
CONF_ACCOUNT_ID: Final = "account_id"
CONF_CUSTOMER_ID: Final = "customer_id"
CONF_CONTRACT_NAME: Final = "contract_name"
CONF_RATE: Final = "rate"
CONF_RATE_OPTION: Final = "rate_option"
CONF_AUTH_MODE: Final = "auth_mode"
CONF_PREHEAT_DURATION: Final = "preheat_duration_minutes"
CONF_HISTORY_DAYS: Final = "history_days"
CONF_CALENDAR_ENTITY_ID: Final = "calendar_entity_id"
CONF_ENABLE_CONSUMPTION_SYNC: Final = "enable_consumption_sync"
CONF_MFA_CODE: Final = "mfa_code"
CONF_AUTH_CLIENT: Final = "auth_client"

# Options form sections
SECTION_ADVANCED: Final = "advanced"

# Auth modes
AUTH_MODE_PORTAL: Final = "portal"
AUTH_MODE_OPENDATA: Final = "opendata"

# Hydro-Québec login clients (the wrapper's ``auth_client`` argument)
AUTH_CLIENT_WEB: Final = "web"
AUTH_CLIENT_MOBILE: Final = "mobile"
AUTH_CLIENTS: Final = [AUTH_CLIENT_MOBILE, AUTH_CLIENT_WEB]

# Defaults
DEFAULT_PREHEAT_DURATION: Final = 120  # minutes
DEFAULT_AUTH_CLIENT: Final = AUTH_CLIENT_MOBILE

# Hydro-Québec only exposes consumption periods 10 days after the contract start,
# or after the move-in notice when it comes later, hence the margin.
NEW_CONTRACT_GRACE_DAYS: Final = 30
NEW_CONTRACT_PERIODS_RETRY_HOURS: Final = 1

# Supported rates
RATE_D: Final = "D"
RATE_DT: Final = "DT"
RATE_DPC: Final = "DPC"
RATE_M: Final = "M"
RATE_M_GDP: Final = "M-GDP"

RATES: Final = [RATE_D, RATE_DT, RATE_DPC, RATE_M, RATE_M_GDP]

# Rate options
RATE_OPTION_CPC: Final = "CPC"
RATE_OPTION_NONE: Final = ""

# Rate option mappings (which options are valid for which rates)
RATE_OPTIONS: Final = {
    RATE_D: [RATE_OPTION_NONE, RATE_OPTION_CPC],
    RATE_DT: [RATE_OPTION_NONE],
    RATE_DPC: [RATE_OPTION_NONE],
    RATE_M: [RATE_OPTION_NONE],
    RATE_M_GDP: [RATE_OPTION_NONE],
}
