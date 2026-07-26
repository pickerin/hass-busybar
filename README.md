# BUSY Bar for Home Assistant

<img src="images/logo.png" alt="BUSY Bar" width="128" align="right">

Local-only Home Assistant integration for the [BUSY Bar](https://busy.app/) by Flipper Devices. Talks directly to the Bar's open HTTP API over your LAN — no cloud, no account.

## Features

- **Auto-discovery** via mDNS (`_busybar._tcp`), or add by IP
- **Busy switch** — start/stop the stock BUSY card (same as the top button, with its app-configured timer/pomodoro)
- **Custom screen switch** — start/stop the selected screen
- **Screen select** — choose which screen the custom card shows (On Air, Meeting, DND, Low Social Battery, Coding, Lunch, and any themes you add)
- **Screen timer** — countdown for the custom screen in minutes; 0 = untimed
- **Mode select** — command the Bar's mode (Busy/Custom/Off/Apps/Settings) from HA; the firmware treats it exactly like moving the physical slider, and a physical move re-syncs it
- **Mode slider sensor** — live position of the 5-way mode slider
- **Event entities** — top button, OK, Back, and scroll wheel, visible in the UI with last-event timestamps
- **Button entities** — press the top button, OK, Back, or scroll the wheel up/down from HA (same firmware path as a real press)
- **State stream diagnostic** — shows whether the real-time WebSocket connection is up
- **Busy status sensor** — `idle` / `busy` / `timer` / `interval`, with time-left and pause attributes
- **Physical controls fire events** — the big top button, OK/BACK, the 5-position mode slider, and the scroll wheel all fire `busybar_event` on the HA event bus in real time (via the Bar's WebSocket state stream), so you can program them to do anything
- **Live state push** — flip busy on the device and the HA switch updates instantly
- **Brightness** and **volume** controls
- **Services** for automations:
  - `busybar.draw_text` — draw text on the front or back display (font, color, position, timeout, scroll)
  - `busybar.clear_display` — clear API-drawn content
  - `busybar.play_audio` / `busybar.stop_audio` — play uploaded or stock sounds
  - `busybar.press_key` — remotely press any physical control

## Installation

### HACS (custom repository)

1. HACS → three-dot menu → **Custom repositories**
2. Add this repository URL, category **Integration**
3. Install **BUSY Bar**, restart Home Assistant

### Manual

Copy `custom_components/busybar/` into your `config/custom_components/` folder and restart.

## Setup

The Bar must be on your Wi-Fi (set up via the BUSY App). Home Assistant should discover it automatically; otherwise add it via **Settings → Devices & Services → Add Integration → BUSY Bar** and enter its IP.

**Enable HTTP API access first (one-time, over USB):** the Bar ships with its network HTTP API disabled. Connect the Bar to a computer via USB, open http://10.0.4.20 in a browser, go to the **Network** tab, and turn on **HTTP API access**. If you set a password there (4-10 digits), enter it as the API password when adding the integration. Cloud API tokens from cloud.busy.app do not work for local LAN access.

## Example automations

Washer finished:

```yaml
alias: Washer done on BUSY Bar
triggers:
  - trigger: state
    entity_id: sensor.washer_status
    to: "finished"
actions:
  - action: busybar.draw_text
    data:
      text: "Washer done!"
      display: back
      color: "#00FF00"
      timeout_ms: 30000
```

Mute the house when you go busy:

```yaml
alias: Quiet house when busy
triggers:
  - trigger: state
    entity_id: sensor.busy_bar_busy_status
    to: "busy"
actions:
  - action: media_player.volume_mute
    target:
      entity_id: media_player.kitchen
    data:
      is_volume_muted: true
```

## Lovelace card

The integration ships a custom card with a **live mirror of the Bar's LED display** (polled once a second) and every control: mode, BUSY/CUSTOM toggles, screen picker, timer, brightness, volume, and the physical buttons. The card registers itself as a Lovelace resource automatically (storage-mode dashboards, i.e. the default; with YAML-mode dashboards add `/busybar-static/busybar-card.js` as a module resource manually). Just add:

```yaml
type: custom:busybar-card
```

Options: `display: back` mirrors the rear OLED instead; `prefix` (default `busy_bar`) matches your entity ids if you renamed the device; `entry_id` selects a Bar when you have several; `entities:` overrides individual roles (`busy`, `custom`, `screen`, `mode`, `timer`, `brightness`, `volume`, `status`, `top`, `ok`, `back`, `up`, `down`), e.g.:

```yaml
type: custom:busybar-card
entities:
  screen: select.busy_bar_busy_screen
```

If the card reports missing roles, your entity ids differ (renamed device or entities created by an older version) — set `prefix` or the specific `entities:` entries.

## Programming the physical controls

Every physical input fires a `busybar_event`. The big top button is `start`:

```yaml
alias: Top button toggles office lights
triggers:
  - trigger: event
    event_type: busybar_event
    event_data:
      type: button
      button: start
      action: press
actions:
  - action: light.toggle
    target:
      entity_id: light.office
```

Event payloads:

| Control | `type` | Fields |
|---|---|---|
| Top button | `button` | `button: start`, `action: press`/`release` |
| OK / Back | `button` | `button: ok`/`back`, `action: press`/`release` |
| Mode slider | `switch` | `position: busy`/`custom`/`off`/`apps`/`settings` |
| Scroll wheel | `encoder` | `delta: <int>` (negative = down) |

Note: the top button still performs its normal on-device action (starting/stopping busy). To use it purely as an HA button, pair your automation with whatever busy state you want, or leave busy features to the mode slider.

## Screens: Busy vs Custom

The Bar has two cards, matching the BUSY and CUSTOM positions of its mode slider:

- **Busy** is the stock red BUSY card. Its look is fixed and its timer follows what you configured in the BUSY App (often a pomodoro). The **Busy** switch starts it.
- **Custom** is the themed screen (On Air, Meeting, ...). The **Screen** select picks the theme, the **Screen timer** sets its countdown (0 = untimed), and the **Custom screen** switch starts it.

Each switch reports "on" only while its own card is running. Stock themes: back_soon, booked, chill_time, coding, dnd, flow, keep_out, low_social_battery, lunch, meeting, on_air, on_call; themes you add to `/ext/apps_assets/busy/themes/` appear automatically. Starting a card from HA takes over the display regardless of the slider position; the slider sensor stays unknown until the slider first moves after an HA restart (the Bar only reports changes).

## Notes

- Polling interval is 10 seconds, but busy state and input events arrive instantly over the WebSocket state stream. Display/audio services fire immediately.
- Brightness reads as unknown while the Bar is in auto-brightness mode; setting a value switches it to manual.
- API shapes follow the official [busylib-py](https://github.com/busy-app/busylib-py) SDK and [BUSY Bar docs](https://docs.busy.app/).

## License

MIT
