# TTS Script Writing Rules

## Sentence Rules
- Maximum 25 words per sentence.
- No parentheticals.
- No semicolons.
- End sentences on strong, meaningful words.

## TTS-Hostile Patterns (NEVER include in scripts)
- No URLs, bullet points, tables, markdown formatting, or citation markers.
- Replace "e.g." with "for example".
- Replace "&" with "and".
- Replace "%" with "percent".
- Replace "$X" with "X dollars".
- Replace all symbols with their spoken equivalents.

## Pronunciation
- Expand ALL acronyms on first use in the script itself. Do NOT rely on qwen3-tts text_expansions.py.
- Spell out numbers under 100 ("forty-two", not "42").
- Write dollar amounts in full words ("fifteen dollars", not "$15").
- Avoid ambiguous homographs: read/read, live/live, lead/lead. Rephrase to remove ambiguity.

## Conversational Rewriting
- Address the listener as "you".
- Use contractions (it's, you'll, that's, we're).
- Use verbal transitions between topics: "so here's the thing", "next up", "alright", "now let's talk about".
- Open with a hook that draws the listener in. Never open by reading a title or heading.

## Chunk Boundary Awareness
- Keep paragraphs under 500 characters (~80-90 words).
- Each paragraph becomes one TTS chunk with independent prosody.
- Start each paragraph with a re-establishing transition so tone carries across chunks.
- End every paragraph on a complete thought. Never leave a dangling clause.
- This prevents tone resets and awkward pauses at chunk boundaries.

## Analogies
- Do NOT use analogies or metaphors by default.
- Only include them if the user explicitly requests via `--analogies` flag or says "include analogies".

## Structure
- Open with 1-2 context-setting sentences that hook the listener.
- Group content into 2-4 natural topic segments with verbal signposts.
- Close with a clear takeaway or call to action. No fade-outs, no trailing summaries.
