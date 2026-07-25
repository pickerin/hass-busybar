# BUSY Bar for Home Assistant

<img src="images/logo.png" alt="BUSY Bar" width="128" align="right">

Local-only Home Assistant integration for the [BUSY Bar](https://busy.app/) by Flipper Devices. Talks directly to the Bar's open HTTP API over your LAN — no cloud, no account.

## Features

- **Auto-discovery** via mDNS (`_busybar._tcp`), or add by IP
- **Busy switch** — start/stop busy mode (timed, untimed, or pomodoro — follows the busy profile)
- **Busy screen select** — choose which screen busy mode shows (On Air, Meeting, DND, Low Social Battery, Coding, Lunch, and any custom themes on the device)
- **Busy timer** — countdown duration in minutes; 0 = untimed
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

## Screen selection

The **Busy screen** select edits the busy profile's theme, so it also changes what the BUSY App shows for that profile. Stock screens: back_soon, booked, chill_time, coding, dnd, flow, keep_out, low_social_battery, lunch, meeting, on_air, on_call. Themes you add to `/ext/apps_assets/busy/themes/` on the device appear automatically.

## Notes

- Polling interval is 10 seconds, but busy state and input events arrive instantly over the WebSocket state stream. Display/audio services fire immediately.
- Brightness reads as unknown while the Bar is in auto-brightness mode; setting a value switches it to manual.
- API shapes follow the official [busylib-py](https://github.com/busy-app/busylib-py) SDK and [BUSY Bar docs](https://docs.busy.app/).

## License

MIT
