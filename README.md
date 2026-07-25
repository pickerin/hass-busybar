# BUSY Bar for Home Assistant

Local-only Home Assistant integration for the [BUSY Bar](https://busy.app/) by Flipper Devices. Talks directly to the Bar's open HTTP API over your LAN — no cloud, no account.

## Features

- **Auto-discovery** via mDNS (`_busybar._tcp`), or add by IP
- **Busy switch** — start/stop busy mode (uses your BUSY profile's own timer settings)
- **Busy status sensor** — `idle` / `busy` / `timer` / `interval`, with time-left and pause attributes
- **Brightness** and **volume** controls
- **Services** for automations:
  - `busybar.draw_text` — draw text on the front or back display (font, color, position, timeout, scroll)
  - `busybar.clear_display` — clear API-drawn content
  - `busybar.play_audio` / `busybar.stop_audio` — play uploaded or stock sounds

## Installation

### HACS (custom repository)

1. HACS → three-dot menu → **Custom repositories**
2. Add this repository URL, category **Integration**
3. Install **BUSY Bar**, restart Home Assistant

### Manual

Copy `custom_components/busybar/` into your `config/custom_components/` folder and restart.

## Setup

The Bar must be on your Wi-Fi (set up via the BUSY App). Home Assistant should discover it automatically; otherwise add it via **Settings → Devices & Services → Add Integration → BUSY Bar** and enter its IP.

If you set the Bar's HTTP access mode to `key`, enter that key as the API key. In the default `enabled` mode no key is needed.

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

## Notes

- Polling interval is 10 seconds. Display/audio services are fired instantly.
- Brightness reads as unknown while the Bar is in auto-brightness mode; setting a value switches it to manual.
- API shapes follow the official [busylib-py](https://github.com/busy-app/busylib-py) SDK and [BUSY Bar docs](https://docs.busy.app/).

## License

MIT
