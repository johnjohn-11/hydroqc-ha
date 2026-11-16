# Hydro-Québec integration for Home Assistant

[Français](README.md) | **English**

<p align="center">
  <img src="https://raw.githubusercontent.com/hydroqc/hydroqc-ha/main/images/logo.png" alt="Hydro-Québec Logo" width="200"/>
</p>

<p align="center">
  Monitor and automate your electricity use directly in Home Assistant.
</p>

**Quick navigation:** [Installation](#installation) • [Configuration](#configuration) • [Services](#services) • [Blueprints](#blueprints) • [Sensors](#sensors) • [Updates](#update-frequency) • [FAQ](#faq)

---

> **⚠️ IMPORTANT - Support**
>
> This integration is developed **independently** and is **not supported by Hydro-Québec**.
>
> **DO NOT CONTACT** Hydro-Québec customer service about problems with this integration.
>
> For questions or problems:
> - 📝 [Open an issue on GitHub](https://github.com/hydroqc/hydroqc-ha/issues)
> - 💬 [Join our Discord](https://discord.gg/5zEpJjppgr)
> - 📖 [Read the documentation](https://hydroqc.ca)

---

## What is it?

A **native** Home Assistant integration that lets you:

- Import your hourly consumption history and show it in Home Assistant's Energy dashboard
- Follow your bills and electricity costs
- Be alerted of critical peak periods
- See your winter credits (rate DCPC)
- Automate your devices during peak periods
- Use a calendar for the best reliability

## Why this integration?

### Reliability, belt and braces

The calendar gives your automations **several layers of protection**:

- **Persistence**: events stay even when the API is unavailable
- **Native Home Assistant triggers**: relies on Home Assistant's proven calendar triggers
- **Manual fallback**: create events yourself if something goes wrong

### Features

- **All supported rates**: D, DT, DPC (Flex-D), DCPC (Winter Credits)
- **No-account mode**: watch the peaks without credentials
- **Several contracts**: home, cottage, and so on
- **Ready-made blueprints**: tuned automations included

---

## Installation

### With HACS (recommended)

**Option 1: one click**

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=hydroqc&repository=hydroqc-ha&category=integration)

Click the badge, then:

1. Click **Download**
2. **Restart Home Assistant**
3. Add the integration in **Settings** → **Devices & services**

**Option 2: custom repository in HACS**

<details>
<summary>Detailed steps</summary>

1. Open **HACS** in Home Assistant
2. Click **Integrations**
3. Click the **3 dots** → **Custom repositories**
4. Add `https://github.com/hydroqc/hydroqc-ha` (category: Integration)
5. Search for **Hydro-Québec** and click **Download**
6. **Restart Home Assistant**

</details>

### Manual installation

<details>
<summary>For advanced users</summary>

1. Download from [GitHub Releases](https://github.com/hydroqc/hydroqc-ha/releases)
2. Extract into `custom_components/hydroqc`
3. Restart Home Assistant

</details>

---

## Configuration

### Option 1: with a Hydro-Québec account (full access)

Access to **all the data**: consumption, billing, peaks, winter credits.

1. **Settings** → **Devices & services** → **+ Add integration**
2. Search for **Hydro-Québec**
3. Choose **Portal (Customer Space login)**
4. Enter your Hydro-Québec credentials
5. Select the contract to follow
6. Done. The sensors appear within about 60 seconds

By default the login uses the client of Hydro-Québec's mobile app, which keeps the session for 90 days. See [Session lifetime](#e-mail-verification) to pick the web portal instead.

### Option 2: public data (no account)

Only the **peak alerts**, without credentials.

1. Follow steps 1 and 2 above
2. Choose **OpenData (no login required)**
3. Select your sector and your rate
4. The peak alerts are active

### Changing contract or password

Hydro-Québec assigns a new contract number each time the person responsible for a consumption location changes, even if that location was already tied to the account. There is no need to remove the integration (account mode only):

1. **Settings** → **Devices & services** → **Hydro-Québec**
2. Entry menu **⋮** → **Reconfigure**
3. Confirm your e-mail. Leave the password empty to keep the current one, or enter the new one
4. Select the contract

The entities keep their `entity_id` and the consumption history is kept. For a new contract, billing data only arrives after about ten days (see the FAQ).

### Password refused or to be changed

When Hydro-Québec refuses the stored password (for example when the portal requires a new one), the integration stops updating and Home Assistant shows **Reauthentication required** in **Settings** → **Devices & services**. Change the password on Hydro-Québec's site first, then click **Reauthenticate** and enter the new one.

### E-mail verification

Hydro-Québec can ask for a verification code sent by e-mail after the password.

**How it goes**

1. During the initial setup, a reconfiguration or a reauthentication, the integration shows the **E-mail Verification** step.
2. Enter the code received by e-mail. Leave the field empty to ask for a new code. If the code has expired, the integration restarts the login and a new code is sent automatically.
3. Once validated, the portal session is kept in Home Assistant's storage (refresh token and Azure AD B2C sign-in cookies). At restart the integration first tries a silent login. The session obtained during the initial setup is reused by the entry it creates: no second code is asked right after adding it.

**No code requested in the background**

Automatic logins (scheduled updates, restarts) stop at the verification step: no code is requested or sent, and the login is not retried in a loop. Home Assistant shows **Reauthentication required** in **Settings** → **Devices & services**. Click **Reauthenticate**, then enter the new code.

**Session lifetime**

The lifetime depends on the login client, chosen in **Settings** → **Devices & services** → **Hydro-Québec** → **Configure** → **Advanced** → **Login client**:

| Client | Session lifetime | Verification code |
|--------|------------------|-------------------|
| **Mobile app** (default) | 90 days, extended at each login | Once, then only if the session expires |
| **Web portal** | 24 hours | Every day |

While the session lasts, Home Assistant restarts ask for neither password nor code. Once it has expired, the integration goes back to **Reauthentication required** and a new code has to be entered.

Switching client reloads the integration and asks for a new code: the session of one client is of no use to the other. The mobile client uses the identifier of Hydro-Québec's official app. If the mobile client stops working, choose the web portal.

### Calendar setup (required for DPC/DCPC)

The calendar is **required** for the DPC (Flex-D) and DCPC (Winter Credits) rates. The peak sensors depend on it.

**Step 1: create a local calendar**

[![Add Local Calendar](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=local_calendar)

Or manually:

1. **Settings** → **Devices & services** → **+ Add integration**
2. Search for **Local Calendar**
3. Create a dedicated calendar (for example "HQ Peaks")

> ⚠️ **Important**: use a dedicated calendar. Do not share it with other integrations.

**Step 2: select it in Hydro-Québec**

1. **Hydro-Québec** → **Configure**
2. Select your dedicated calendar
3. Peak events are synced automatically

If the calendar cannot be found after several attempts, the sync stops until the next restart and a repair issue appears in **Settings** → **System** → **Repairs**.

---

## Services

### `hydroqc.refresh_data`

Refreshes a contract's data at once, without waiting for the next scheduled update. Target any entity of the integration.

```yaml
action: hydroqc.refresh_data
target:
  entity_id: sensor.hydro_quebec_home_balance
```

### `hydroqc.sync_consumption_history`

Imports the hourly consumption history into the statistics of the Energy dashboard (account mode only, with consumption sync enabled). The import runs in the background and can take several minutes. Target an entity or the contract's device.

| Parameter | Description | Required |
|-----------|-------------|----------|
| `days_back` | Number of days of history to import (731 by default, about 2 years) | No |

```yaml
action: hydroqc.sync_consumption_history
data:
  days_back: 365
target:
  entity_id: sensor.hydro_quebec_home_balance
```

### `hydroqc.create_peak_event`

Creates a critical peak event in the calendar by hand. Useful to:

- Prepare your automations before the official announcement (extreme weather ahead)
- Test your blueprints with a real event
- Fall back when the API is unavailable

| Parameter | Description | Required |
|-----------|-------------|----------|
| `device_id` | The Hydro-Québec device (contract) | Yes |
| `date` | Date of the event | Yes |
| `time_slot` | `AM` (6h-10h) or `PM` (16h-20h) | Yes |

```yaml
action: hydroqc.create_peak_event
data:
  device_id: abc123def456
  date: "2026-02-15"
  time_slot: "PM"
```

> **Note**: the event uses the same UID format as the OpenData events. If Hydro-Québec then announces the same peak, the existing event is kept (no duplicate).

---

## Blueprints

Ready-made automations to handle peak periods.

### Winter Credits blueprint (DCPC)

For rate D with Winter Credits (CPC).

[![Import the blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fhydroqc%2Fhydroqc-ha%2Fblob%2Fmain%2Fblueprints%2Fwinter-credits-calendar.yaml)

**Features**:

- Calendar triggers for critical peaks, fixed schedule for regular peaks
- Pre-heating before critical peaks (1h45 before by default)
- Separate actions for critical and regular peaks
- Anchor periods (morning and evening)
- Built-in random delay at the end of a peak (30 s to 5 min)

**Daily schedule (regular peaks)**:

| Period | Hours |
|--------|-------|
| Morning anchor | 01h-04h |
| Morning peak | 06h-10h |
| Evening anchor | 12h-14h |
| Evening peak | 16h-20h |

### Flex-D blueprint (DPC)

For the Flex-D (DPC) rate.

[![Import the blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fhydroqc%2Fhydroqc-ha%2Fblob%2Fmain%2Fblueprints%2Fflex-d-calendar.yaml)

**Features**:

- Calendar triggers only (critical peaks)
- Configurable pre-heating (2h before by default)
- Actions at the start and at the end of a peak
- Built-in random delay at the end of a peak (30 s to 5 min)

### Testing your blueprints

After importing a blueprint and creating your automation, **create a test event** in your calendar to check that everything works:

1. Use the `hydroqc.create_peak_event` service to create an event
2. Check that your actions run as expected
3. You can delete the test event afterwards

### Understanding the blueprint parameters

#### Pre-heat offset

Set the pre-heating separately for morning and evening peaks.

**Format**: `-HH:MM:SS` (negative means before the event)

#### Offset before the peak starts (Flex-D only)

- **Default**: `-00:01:00` (1 minute before)
- **Purpose**: lets your devices settle before the peak
- **Example**: peak at 18:00 → actions at 17:59

#### Parallel actions

Actions run at the same time instead of one after the other, so if one fails the others still run.

```yaml
- parallel:
    - action: climate.set_temperature
      target:
        entity_id: climate.bedroom
      data:
        temperature: 19
    - action: switch.turn_off
      target:
        entity_id: switch.water_heater
```

#### Random delay at the end of a peak

The blueprints add a random delay (30 seconds to 5 minutes) at the end of peaks.

- **Reason**: avoids overloading the power grid
- **Effect**: devices do not all restart at the same moment
- **Recommendation**: keep this delay in your own actions

---

## Sensors

### Account sensors (account mode only)

| Sensor | Description |
|--------|-------------|
| **Balance** | Current account balance |
| **Billing period** | Current day, duration, projected bill |
| **Consumption** | Daily mean, total, projection |
| **Cost** | Mean cost per kWh, daily bill |
| **Temperature** | Mean temperature of the period |
| **Outage** | Next or current outage with details |

### Rate-specific sensors

<details>
<summary><strong>Rate DCPC (Winter Credits)</strong></summary>

- Cumulated winter credit
- Projected winter credit
- Anchor and peak start and end times
- Yesterday's peak performance
- Critical peak indicators
- Pre-heat alerts

</details>

<details>
<summary><strong>Rate DPC (Flex-D)</strong></summary>

- Current DPC period details
- Next peak start and end times
- Pre-heat start time
- Number of critical hours
- Number of winter days
- Critical peak alerts

</details>

<details>
<summary><strong>Rates DT / DPC</strong></summary>

- Consumption at the higher and lower prices
- Net saving or loss versus rate D

</details>

---

## Update frequency

The integration queries Hydro-Québec in time windows (Montréal time), with an offset of its own for each installation to spread the calls.

| Source | Frequency |
|--------|-----------|
| **Open data** (peaks) | Every 15 minutes from 10:30 to 15:00, hourly the rest of the time. Winter season only (December 1 to March 31) |
| **Customer Space** (balance, billing, credits) | Hourly from midnight to 8:00, every 3 hours the rest of the time |
| **Hourly consumption** | Hourly, after a Customer Space update |
| **Peak calendar** | Read again every 15 minutes during the winter season |

The `hydroqc.refresh_data` service forces an update at once.

---

## Diagnostics

To attach a report to an issue: **Settings** → **Devices & services** → **Hydro-Québec** → entry menu **⋮** → **Download diagnostics**. The e-mail, the password, the customer, account and contract numbers and the contract name are redacted.

---

## Removing the integration

1. **Settings** → **Devices & services** → **Hydro-Québec**
2. Entry menu **⋮** → **Delete**

The portal session and the list of calendar events kept by the integration are erased. Two things stay and are removed by hand:

- The imported consumption statistics (`hydroqc:...`), in **Developer tools** → **Statistics**
- The peak events already created in your calendar

---

## Known limitations

- An entry follows a single contract. Add the integration once per contract.
- The DPC and DCPC rates require a calendar: without one, the peak sensors are not created.
- Open data peaks are only published during the winter season.
- Hydro-Québec does not provide hourly consumption for 2 to 3 days around a change of billing period.
- For a new contract, billing data only arrives after about ten days.
- The integration relies on undocumented interfaces of Hydro-Québec's portal, which can change without notice.

---

## FAQ

<details>
<summary><strong>Login fails</strong></summary>

- Check your credentials on [Hydro-Québec](https://session.hydroquebec.com/)
- Check the special characters in the password
- Make sure the account has active contracts

</details>

<details>
<summary><strong>No data shows up</strong></summary>

- Wait 60 seconds for the first update
- Check the logs: **Settings** → **System** → **Logs**
- Check that Hydro-Québec's portal is online

</details>

<details>
<summary><strong>New contract: billing sensors unknown</strong></summary>

- Hydro-Québec only exposes the consumption portrait about 10 days after the contract starts (or after the move-in notice when it comes later)
- Meanwhile a single warning "Consumption periods are not available yet" is logged, the balance and the outages stay up to date and the consumption sync waits
- The data is requested again every hour and the sensors fill in as soon as it is available

</details>

<details>
<summary><strong>Sensors unavailable or unknown</strong></summary>

- Sensors become **unavailable** when the update fails: portal offline, portal error or reauthentication required. The portal status sensor stays available to report the outage
- Seasonal sensors (winter credits: December to March) show **unknown** off-season
- Check whether your rate supports the sensor
- Check the logs: **Settings** → **System** → **Logs**

</details>

<details>
<summary><strong>The calendar does not sync</strong></summary>

- Check that the local calendar is installed
- Check that the calendar is selected in the options
- Reload the integration after configuring it
- Check **Settings** → **System** → **Repairs** and the logs for validation errors

</details>

---

## Migrating from hydroqc2mqtt

Already using the add-on or hydroqc2mqtt?

- **Can run side by side**: test safely
- **Same sensor names**: only the prefix changes
- **New calendar blueprints**: more reliable than the earlier ones

**Steps**:

1. Install the integration side by side
2. Test your automations with the new sensors
3. **Replace your old blueprints** with the calendar blueprints of this repository
   - The hydroqc2mqtt blueprints relied on binary sensors (less reliable)
   - The new blueprints rely on the calendar
   - Delete your old automations based on the old blueprints
   - Import the new blueprints (import links in the [Blueprints](#blueprints) section)
4. Once satisfied, turn the old system off

---

## Development

Want to contribute? See [CONTRIBUTING.md](CONTRIBUTING.md) for the development environment, the contribution guidelines, the tests and the code conventions.

---

## Resources

- **Documentation**: [hydroqc.ca](https://hydroqc.ca)
- **Issues**: [GitHub Issues](https://github.com/hydroqc/hydroqc-ha/issues)
- **Source code**: [GitHub repository](https://github.com/hydroqc/hydroqc-ha)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

## Related projects

- **hydroqc2mqtt**: [MQTT daemon](https://gitlab.com/hydroqc/hydroqc2mqtt), the predecessor of this integration
- **Hydro-Quebec-API-Wrapper**: the underlying [Python library](https://github.com/hydroqc/hydroqc)

---

## License

This project is licensed under **AGPL-3.0**. See the [LICENSE](LICENSE) file for details.

## Credits

Developed by the [Hydroqc team](https://hydroqc.ca).

---

## Disclaimer

This integration is **not approved by, associated with or supported by Hydro-Québec**.

The name "Hydro-Québec", the logos and all trademarks and registered trademarks in this repository are the property of Hydro-Québec. Their use in this project is for identification only and implies no approval or affiliation.
