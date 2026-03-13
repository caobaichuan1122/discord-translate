# Discord Translate Bot

A Discord bot that joins voice channels and provides real-time speech-to-text translation.

## Features

- Joins a voice channel and provides real-time speech-to-text translation
- Translates text messages directly via slash command
- Transcribes audio using Whisper (local or OpenAI API)
- Translates using Google Translate, DeepL, or OpenAI GPT
- Outputs translated text as an embed in the text channel

## Slash Commands

| Command | Description |
|---|---|
| `/join` | Join your current voice channel and start translating |
| `/leave` | Stop translating and leave the voice channel |
| `/translate <text> [target]` | Translate a text message (optionally specify target language) |
| `/settings` | View current configuration |
| `/set_lang <code>` | Change target language (e.g. `zh`, `en`, `ja`, `ko`, `fr`) |

## Providers

**Speech-to-Text (STT)**

| Provider | Cost | Notes |
|---|---|---|
| `whisper_local` | Free | Runs locally, no API key needed |
| `openai_whisper` | Paid | OpenAI Whisper API, faster |

**Translation**

| Provider | Cost | Notes |
|---|---|---|
| `google_free` | Free | Unofficial Google Translate, no key needed |
| `deepl` | Free tier / Paid | 500k chars/month free tier |
| `openai_gpt` | Paid | GPT translation, most context-aware |

## Setup

### Prerequisites

- Python 3.10+
- ffmpeg

### Installation

```bash
# Clone the repo
git clone <your-repo-url>
cd discord-translate

# Run the deploy script (Ubuntu)
bash deploy.sh
```

### Configuration

Copy `.env.example` to `.env` and fill in your values:

```env
DISCORD_TOKEN=your_discord_bot_token

# Provider selection
STT_PROVIDER=whisper_local        # whisper_local | openai_whisper
TRANSLATE_PROVIDER=google_free    # google_free | deepl | openai_gpt

# Language
SOURCE_LANG=auto
TARGET_LANG=zh

# Whisper local model size
WHISPER_MODEL=base                # tiny | base | small | medium | large

# API Keys (only needed for paid providers)
OPENAI_API_KEY=
DEEPL_API_KEY=

# Recording
RECORDING_INTERVAL=5              # seconds between each transcription
MIN_AUDIO_SECONDS=0.5
```

### Service Management

```bash
sudo systemctl start discord-translate
sudo systemctl stop discord-translate
sudo systemctl restart discord-translate
sudo journalctl -u discord-translate -f
```

## Deployment (CI/CD)

This repo uses GitHub Actions for automatic deployment on push to `main`/`master`.

Required GitHub Secrets:

| Secret | Description |
|---|---|
| `SERVER_HOST` | Server IP or hostname |
| `SERVER_USER` | SSH username |
| `SERVER_SSH_KEY` | SSH private key |
| `SERVER_PORT` | SSH port (default: 22) |
| `BOT_DIR` | Bot directory on the server |
