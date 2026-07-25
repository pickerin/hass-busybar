"""Constants for the BUSY Bar integration."""

DOMAIN = "busybar"

CONF_API_KEY = "api_key"

DEFAULT_PORT = 80
UPDATE_INTERVAL_SECONDS = 10

APPLICATION_NAME = "homeassistant"

# Snapshot type -> sensor state
BUSY_STATE_MAP = {
    "NOT_STARTED": "idle",
    "INFINITE": "busy",
    "SIMPLE": "timer",
    "INTERVAL": "interval",
}

FONTS = [
    "tiny",
    "small",
    "normal",
    "condensed",
    "bold",
    "large",
    "extra_large",
    "global",
]

SERVICE_DRAW_TEXT = "draw_text"
SERVICE_CLEAR_DISPLAY = "clear_display"
SERVICE_PLAY_AUDIO = "play_audio"
SERVICE_STOP_AUDIO = "stop_audio"
