---
name: generate-audio
description: >
  Convert documents to conversational audio via local TTS. Use when the user says
  'convert to audio', 'make audio', 'read this aloud', 'text to speech',
  'TTS', 'explain this and make an MP3', 'audio summary', 'narrate this',
  'spoken version', 'audio briefing', 'podcast version', 'generate audio'.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
---

# Text-to-Audio Generator

When triggered, run the `/generate-audio` command with the user's request. This skill is the natural-language entry point for the TTS pipeline.

## How to proceed

1. Parse the user's message for source file, duration preference, preset, speaker, and whether analogies are requested.
2. Execute the full generate-audio workflow as described in the generate-audio command.
