# text-to-audio

Convert documents to conversational audio using local qwen3-tts.

## Prerequisites

- [Qwen3-TTS](https://github.com/nicoboss/qwen3-tts-cli) installed in a conda environment
- NVIDIA GPU with ~4GB free VRAM
- ffmpeg installed (`sudo apt install ffmpeg`)

## Install

```bash
claude plugins install text-to-audio@local
```

Or manually: ensure the plugin is in `~/.claude/plugins/cache/local/text-to-audio/1.0.0/` and registered in `installed_plugins.json` and `settings.json`.

## Required Permissions

Add these to `~/.claude/settings.json` under `permissions.allow`:

```
Bash(ffmpeg:*)
Bash(nvidia-smi:*)
Bash(ffprobe:*)
```

The plugin also uses `Bash(conda run:*)` and `Bash(curl:*)` which you likely already have permitted.

## Usage

```
/generate-audio report.md --duration 5m --preset casual-briefing
/generate-audio notes.md --preset technical-explainer --speaker Vivian
/generate-audio article.md --duration 10m --analogies
```

Or say: "convert this to audio", "make an audio version", "TTS this document".

## Presets

- **casual-briefing** (default): Friendly, conversational. Speaker: Sohee.
- **technical-explainer**: Adaptive calibration based on user's knowledge. Speaker: Vivian.
- **news-summary**: Professional broadcast tone. Speaker: Dylan.
- **personal-assistant**: Warm, knowledgeable friend. Speaker: Dylan.

## Available Voices

Dylan, Vivian, Sohee, Aiden, Eric, Ryan, Serena, Ono_Anna, Uncle_Fu

## Configuration

Config lives at `~/.claude/tts-config.json` (created on first run):

```json
{
  "qwen3_tts_path": "~/Projects/qwen3-tts",
  "conda_env": "qwen3-tts",
  "default_speaker": "Dylan",
  "default_preset": "casual-briefing",
  "default_duration": "5m",
  "discord_webhook_url": null
}
```

Set `discord_webhook_url` to a Discord webhook URL to get notifications with the MP3 attached when generation completes.

## Output

For input `report.md`, generates:
- `report-script.txt` — the conversational TTS script
- `report.wav` — raw audio
- `report.mp3` — compressed audio (128k)

## Discord Delivery

If a Discord webhook is configured, the MP3 is sent as a file attachment (up to 25MB) when generation completes. Plays inline in the Discord mobile app.
