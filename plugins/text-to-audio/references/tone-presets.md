# Tone Presets

All presets: no analogies by default, overridable with `--analogies`.

## casual-briefing (default)
- **Prosody**: `"casual and encouraging, moderate pace"`
- **Speaker**: Sohee
- **Rules**: Contractions, short sentences, "you" address, rhetorical questions OK, friendly tone.

## technical-explainer
- **Prosody**: `"clear and precise, measured pace"`
- **Speaker**: Vivian
- **Calibration**: Adaptive — three tiers inferred from user's own words (NOT Claude's explanations).
  - **Expert**: Precise jargon, explain only novel concepts in context.
  - **Intermediate**: Mostly plain English, explain jargon in context, build understanding.
  - **Beginner**: Spaced repetition, plain English, explicitly define all terms and acronyms, not condescending.
- **Rules**: Expand acronyms on first use. Tier determines jargon density. Build understanding progressively.
- If insufficient context OR highly technical subject: ask 1-2 quick questions to calibrate.
- Default tier: intermediate.

## news-summary
- **Prosody**: `"professional broadcast tone, steady pace"`
- **Speaker**: Dylan
- **Rules**: Inverted pyramid (conclusion first). Attribute claims. Neutral tone. No "you" address.

## personal-assistant
- **Prosody**: `"warm and conversational, natural pace, like talking to a knowledgeable friend"`
- **Speaker**: Dylan
- **Rules**: Read `~/.claude/user-profile.md` if it exists. Friendly, like a smart research assistant. Fact-check and verify claims. Actionable advice, tailored explanations. Never assume understanding from passive listening — only from user's explicit statements or demonstrated knowledge.
- **Note**: Basic version. Full PA tracking system is a separate project.
