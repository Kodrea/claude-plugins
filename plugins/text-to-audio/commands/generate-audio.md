---
description: >
  Convert documents to conversational audio. Use when the user says
  'convert to audio', 'make audio', 'read this aloud', 'text to speech',
  'TTS', 'explain this and make an MP3', 'audio summary', 'narrate this',
  'spoken version', 'audio briefing', 'podcast version'.
argument-hint: "<file> [--duration 5m] [--preset casual-briefing|technical-explainer|news-summary|personal-assistant] [--speaker Aiden] [--analogies]"
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion]
---

# Text-to-Audio Generator

Convert a document into a conversational audio file using local qwen3-tts.

## Arguments

$ARGUMENTS

Parse for:
- **file** (positional): path to source document
- **--duration**: target duration (default from config, e.g. "5m", "10m")
- **--preset**: tone preset — `casual-briefing` | `technical-explainer` | `news-summary` | `personal-assistant`
- **--speaker**: TTS speaker voice (overrides preset default)
- **--analogies**: include analogies/metaphors in the script (off by default)

---

## Step 0: Load Configuration

Read `~/.claude/tts-config.json`. If it does not exist, create it with these defaults:

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

If `discord_webhook_url` is null, ask the user:
> Would you like to set up Discord notifications for TTS progress? If yes, go to Server Settings > Integrations > Webhooks > New Webhook, copy the URL, and paste it here. If no, progress will only appear in the background task log.

Save the URL to config if provided. If declined, proceed without Discord.

---

## Step 1: Identify Source

- If no file in arguments, search CWD for .md files using Glob and ask the user which one.
- Read the source file.
- Count source words (use `wc -w` on the file).

---

## Step 2: Collect Parameters

Resolve all parameters with this priority: explicit args > inline user instructions > config defaults.

- **Target duration**: from `--duration`, or ask (default from config).
- **Preset**: from `--preset`, or detect from context, or ask. Default from config.
- **Speaker**: from `--speaker`, or preset default (casual-briefing=Sohee, technical-explainer=Vivian, news-summary=Dylan, personal-assistant=Dylan).
- **Analogies**: OFF unless `--analogies` flag present or user explicitly says "include analogies".
- Parse duration string to minutes (e.g. "5m" -> 5, "10m" -> 10).

---

## Step 3: GPU Pre-Check

Run:
```bash
nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits
```

- If free VRAM < 4096 MB: **HARD BLOCK**. Do NOT proceed.
  - Run full `nvidia-smi` to show what's using VRAM.
  - Tell user: "Insufficient VRAM (need ~4GB free for 1.7B model). Here's what's using your GPU:"
  - Show the nvidia-smi output.
  - Suggest: kill competing processes, or wait for them to finish.
- If free VRAM >= 4096 MB: proceed.

---

## Step 4: Technical Calibration (technical-explainer preset ONLY)

Skip this step entirely for other presets.

Scan the conversation history for the **user's own statements** to infer their knowledge level. Focus on:
- What the USER said or demonstrated (their words, questions, terminology used)
- NOT what Claude explained to them (they may not have understood it)

Three tiers:
- **Expert**: User uses precise jargon naturally. Script: jargon OK, explain only novel concepts in context.
- **Intermediate**: User understands basics but isn't deeply technical. Script: mostly plain English, explain jargon in context, build understanding.
- **Beginner**: User is new to the topic. Script: spaced repetition, plain English, define all terms and acronyms, never condescending.

If conversation context is insufficient (new conversation, no prior discussion of the topic) OR the subject is highly technical:
- Ask 1-2 quick calibration questions using AskUserQuestion. Example: "How familiar are you with [topic]? For example, do terms like [X] and [Y] mean anything to you?"

Default to intermediate if ambiguous.

---

## Step 5: Content Triage

Calculate the word budget: `target_minutes * 150` (words per minute at moderate pace).

Read `references/duration-table.md` for reference.

- If source word count <= 1.5x word budget: rewrite the full document. Tell user: "Source fits within budget — rewriting in full."
- If source word count > 1.5x word budget: draft a section outline showing what will be included vs excluded. Use AskUserQuestion to confirm with user before proceeding.

---

## Step 6: Write the TTS Script

**You (Claude) are the rewriter.** Do not delegate this to qwen3-tts.

Before writing, read these reference files:
- `references/script-writing-rules.md` — mandatory rules for all scripts
- `references/tone-presets.md` — constraints for the selected preset

If personal-assistant preset: also read `~/.claude/user-profile.md` if it exists (skip silently if not found).

Key rules:
- Expand ALL acronyms and domain-specific terms to their spoken form directly in the script text.
- Do NOT rely on qwen3-tts text_expansions.py — it has project-specific expansions that may mangle other content.
- Follow all rules in script-writing-rules.md strictly.
- If `--analogies` was NOT specified, do NOT include analogies or metaphors.

Determine the output directory. Use the same directory as the source file. Derive the output name from the source filename (strip extension).

Write the script to: `{output-dir}/{source-name}-script.txt`

After writing, verify word count:
```bash
wc -w {script-path}
```

If word count is outside +/- 15% of the budget, rewrite to hit the target. Report the word count to the user.

---

## Step 7: Generate Audio (Background with Discord Progress)

Read the config for `qwen3_tts_path` and `conda_env`.

Look up the prosody instruction for the selected preset from `references/tone-presets.md`:
- casual-briefing: `"casual and encouraging, moderate pace"`
- technical-explainer: `"clear and precise, measured pace"`
- news-summary: `"professional broadcast tone, steady pace"`
- personal-assistant: `"warm and conversational, natural pace, like talking to a knowledgeable friend"`

Run TTS generation:
```bash
conda run -n {conda_env} --cwd {qwen3_tts_path} \
  python -m qwen3_speak \
  -f {script-path} \
  -o {output-dir}/{name}.wav \
  -s {speaker} -l English \
  -i "{prosody-instruction}" \
  -F wav -v
```

Use `timeout: 600000` (10 minutes) on the Bash call.
Use `run_in_background: true` so the user isn't blocked.

If Discord webhook is configured, send a start notification:
```bash
curl -s -H "Content-Type: application/json" \
  -d '{"content": "🎙️ TTS generating: {name} ({word_count} words, ~{est_duration})"}' \
  "{discord_webhook_url}"
```

Wait for the background task to complete (you'll be notified via TaskOutput).

When it completes, if Discord is configured, send a completion notification.

If the TTS command fails:
- Check if conda env exists: `conda env list | grep qwen3-tts`
- Check if the module path is correct — `--cwd` must point to the qwen3-tts project dir.
- Report the error clearly and suggest fixes.

---

## Step 8: Convert to MP3

```bash
ffmpeg -y -i {output-dir}/{name}.wav -b:a 128k {output-dir}/{name}.mp3
```

After conversion, verify the MP3:
```bash
test -s {output-dir}/{name}.mp3 && echo "MP3 OK" || echo "MP3 MISSING OR EMPTY"
```

If ffmpeg fails or produces a zero-byte file:
- Report the error.
- Note that the .wav file is still available and usable.
- Suggest checking disk space or ffmpeg codec support: `ffmpeg -codecs | grep mp3`

---

## Step 9: Verify and Report

Get the actual audio duration:
```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 {output-dir}/{name}.wav
```

Get file sizes:
```bash
ls -lh {output-dir}/{name}.wav {output-dir}/{name}.mp3
```

Report to the user:
- WAV path and size
- MP3 path and size
- Actual audio duration (formatted as m:ss)
- Target duration for comparison
- Speaker used
- Word count of script
- Preset used

If actual duration differs from target by more than 20%:
- Offer to adjust the script word count and regenerate.

If Discord webhook is configured, send the MP3 as a file attachment for mobile playback:
```bash
# Get MP3 size in bytes
mp3_bytes=$(stat -c%s "{output-dir}/{name}.mp3" 2>/dev/null || echo 0)

if [ "$mp3_bytes" -gt 0 ] && [ "$mp3_bytes" -lt 26214400 ]; then
  # Under 25MB — attach the file
  curl -s -F "file1=@{output-dir}/{name}.mp3" \
    -F 'payload_json={"content":"Audio ready: {title}"}' \
    "{discord_webhook_url}"
else
  # Over 25MB or missing — text-only fallback
  curl -s -H "Content-Type: application/json" \
    -d '{"content":"Audio ready: {title} (file too large to attach)"}' \
    "{discord_webhook_url}"
fi
```

---

## Troubleshooting Reference

- **GPU OOM during generation**: Model may auto-fall back to 0.6B. If that also OOMs, suggest killing competing GPU processes.
- **`conda run` fails**: Verify env exists: `conda env list | grep qwen3-tts`
- **"Module not found"**: Must use `--cwd {qwen3_tts_path}` for module path resolution.
- **Chunk boundary tone resets**: Paragraphs must be < 500 chars. See script-writing-rules.md.
- **Duration significantly off target**: Adjust word count in script, rewrite, regenerate.
- **ffmpeg not found**: Suggest `sudo apt install ffmpeg`.
- **ffmpeg produces 0-byte MP3**: Check disk space. Check codec: `ffmpeg -codecs | grep mp3`.
- **Discord webhook fails**: Verify URL in `~/.claude/tts-config.json`. Test with: `curl -d '{"content":"test"}' "{url}"`.
