# Crimson Chin Long-Form Content Plan

## Purpose

Build a voice-first long-form content engine for The Crimson Chin Post. Allan talks naturally. The pipeline turns that recording into an editable, visually rich football commentary episode and shorter versions without forcing a word-for-word script.

The long-form master is horizontal 16:9. The same editable timeline produces vertical 9:16 Shorts, Reels, and TikToks.

## Core promise

The visuals must mirror what Allan is saying and the football culture behind it.

The system should understand the event, the people involved, the statistics, the online reaction, the meme, the joke, and the emotional point. It should find the most exact visual connected to that moment rather than decorate the speech with generic B-roll.

## User workflow

1. Allan records a natural talking performance or imports a livestream-style recording.
2. The pipeline transcribes and analyzes the recording.
3. It detects editorial moments and builds a moment map.
4. It inspects what the raw footage already shows.
5. It preserves useful existing visuals and actively enhances them when that improves the moment.
6. It researches and retrieves missing supporting assets.
7. It assembles an editable long-form timeline.
8. Allan reviews the timeline, changes any decision, and locks approved moments.
9. The pipeline renders the horizontal master and derives short-form cuts.

## Input handling

The pipeline must inspect the source before deciding how to edit it. Inputs may include a clean talking-head recording, a livestream with browser windows, an existing show layout, a screen recording, a match reaction, or a mixed video containing graphics and references.

It should detect:

- Presenter position and framing.
- Browser windows and screen shares.
- Existing graphics, scoreboards, captions, overlays, and branding.
- Embedded clips and their audio.
- Music, room tone, speech, and effects.
- Existing cuts, pauses, dead air, and repeated sections.
- Whether the existing visual already communicates the current point.

Useful existing visuals are preserved as the base. They may be reframed, highlighted, animated, polished, or layered with graphics. The system must not automatically replace a useful visual merely because another asset is available.

## Moment map

Each spoken section becomes a structured moment with timestamps, transcript, entities, context, emotion, and editorial treatment.

The classifier should detect as many relevant signals as practical, including:

- Hook, setup, development, payoff, and conclusion.
- Claims, opinions, explanations, predictions, and questions.
- Jokes, punchlines, sarcasm, callbacks, irony, and trolling.
- Emotional rises, disbelief, anger, excitement, pauses, and reactions.
- Names, clubs, players, managers, journalists, competitions, locations, dates, and events.
- Quotes, paraphrases, press-conference statements, articles, posts, and video references.
- Match results, goals, transfers, tactical claims, controversies, and fan arguments.
- Stats, comparisons, records, league position, form, xG, shots, possession, passing, tackles, fees, and historical context.
- Meme language, repeated spam, viral comments, running jokes, rivalry references, and football-culture context.
- Moments that deserve a chapter break, visual reveal, quote card, stat card, reaction, or short-form extraction.

Each moment records a visual mode such as:

- `HOST_PRIMARY`
- `SOURCE_PRIMARY`
- `SPLIT_SCREEN`
- `EXISTING_VISUAL_ENHANCED`
- `FULL_SCREEN_QUOTE`
- `MUTED_VIDEO_REFERENCE`
- `STAT_CARD`
- `MEME_OR_REACTION`
- `TACTICAL_DIAGRAM`
- `REACTION_BEAT`
- `VISUAL_METAPHOR`

## Visual sourcing

Search is event-grounded. The query combines the relevant person, club, match, date, claim, quote, and platform instead of searching for a generic topic.

The asset system should retrieve and track:

- The exact match or goal being discussed.
- The relevant press-conference image, quote, or clip.
- Articles and reports about the event.
- X posts, viral threads, comments, and reaction screenshots.
- Memes being spammed after a result.
- Fan-recorded footage where it illustrates the moment.
- Official club, league, or player media.
- Player, manager, stadium, trophy, and club images.
- Tables, charts, tactical maps, shot maps, and stat graphics.
- Search-result and AI/search-summary screenshots when they are part of the conversation.
- Sound effects and music from the local asset library.

Every asset stores its source URL or filename, creator, timestamp, rights status, topic, related entity, and intended use.

If the exact asset cannot be found, the system creates a clear fallback request:

```text
Missing asset: Xabi Alonso press-conference clip
Moment: 04:12–04:16
Search: Xabi Alonso press conference [topic] [date]
Place file: assets/incoming/04-12_xabi_press_clip.mp4
Purpose: show the exact statement being discussed
```

## Visual treatment

Every important visual should pop with an intentional treatment. The system chooses the treatment that fits the moment, such as:

- Punch-in, reframing, pan, or keyframe motion.
- Highlight, outline, arrow, label, or spotlight.
- Stat animation or comparison bar.
- Quote card with the speaker’s face and source.
- Meme, reaction, or comment reveal.
- Browser or article crop focused on the relevant line.
- Muted video reference playing while Allan explains it.
- Tactical diagram or visual metaphor.
- Color, contrast, lighting, skin, and compositing polish.
- Transition, impact, riser, silence, or short sound effect.

The system should add energy and clarity without replacing a useful source. Some moments may intentionally stay calmer so a joke, quote, or argument can breathe.

## Stats and evidence

When Allan mentions a statistic, the system should connect the number to the subject:

- Player image plus the metric.
- Manager image plus the record.
- Club badge plus league position or spending.
- Stadium image plus attendance or home form.
- Player cutout plus comparison chart.
- Match image plus match statistics.

Stats are sourced, timestamped, and cited. Conflicting or uncertain numbers are flagged for review rather than presented as certain.

## Audio plan

The voice remains the anchor. The system analyzes speech intensity, pauses, emotion, and existing audio before adding anything.

Audio treatments include:

- Preserve useful original livestream audio.
- Remove dead air and repeated sections while retaining natural delivery.
- Keep dialogue clear and dominant.
- Use short effects on visual hits, jokes, reveals, and transitions.
- Use music only when it supports the section and never as an automatic layer.
- Use silence deliberately before a punchline or serious point.
- Mute referenced clips when Allan is explaining them; retain source audio only when it adds useful context.
- Maintain precise profanity censorship and room-tone replacement when required.
- Check waveform timing, peaks, clipping, and dialogue-to-effect balance.

## Long-form structure

The editor should discover the structure from the recording, then shape it into:

1. Hook: the strongest claim, reaction, or question.
2. Context: what happened and why it matters.
3. Main argument: the first evidence-backed point.
4. Development: examples, clips, stats, quotes, memes, and counterpoints.
5. Escalation: the funniest, most surprising, or most emotional section.
6. Resolution: what the evidence means.
7. Closing: final opinion, joke, question, or call to action.

The user does not need to read this structure as a script. The recording is shaped into it after the fact.

## Editable review interface

The review screen shows the video preview, timeline, transcript, moment labels, sources, and asset decisions. Every cut, caption, keyframe, transition, effect, source, and generated choice stays accessible.

Each moment can be marked:

- Keep.
- Enhance.
- Replace.
- Remove.
- Try another.
- Lock.

All changes are non-destructive. Regenerating one moment must not rewrite locked moments or rebuild the entire episode unnecessarily.

## Local reference mode and publishing mode

The private local draft may use the strongest available reference asset to show the intended creative treatment. Each item carries a rights label and remains replaceable.

The publishing stage performs a separate review of broadcaster footage, music, screenshots, articles, memes, fan footage, and unknown sources. It can swap an asset for a licensed, public-domain, user-supplied, or original alternative while preserving the timing and treatment.

## Output package

Each approved project produces:

- Horizontal 16:9 long-form master.
- Vertical 9:16 Shorts/Reels/TikToks.
- Transcript and caption files.
- Chapters and a description draft.
- Thumbnail and title candidates.
- Source and rights manifest.
- Editable timeline and decision history.
- Review contact sheet and QA report.

## Performance design

Time and space efficiency are core product requirements, alongside editorial quality. The system should make strong creative decisions without repeatedly loading, copying, or re-analyzing the same media.

Priority order:

1. Preserve the meaning and quality of Allan’s words.
2. Preserve useful source visuals and make the right moment pop.
3. Keep the project editable and recoverable.
4. Keep time complexity close to linear.
5. Keep memory and disk usage bounded through streaming, proxies, caching, and cleanup.

The system should use linear processing where possible:

- Hash-table lookups for cached transcripts, assets, and scene decisions.
- One transcription reused across all outputs.
- Cached web research, screenshots, embeddings, and proxy media.
- Indexed asset retrieval instead of comparing every moment with every asset.
- Scene-level rendering so one change does not rebuild the whole episode.
- Parallel work for independent searches and asset preparation.
- Temporary-file cleanup after export.

Space requirements:

- Stream long recordings instead of loading the entire episode into memory.
- Use low-resolution proxy media during analysis and editing.
- Store one canonical copy of each source asset and reference it by hash.
- Keep transcripts, moment maps, metadata, and edit instructions lightweight.
- Cache expensive results such as transcription, scene detection, image embeddings, and web research.
- Render only changed scenes and reuse unchanged scene outputs.
- Keep temporary files in a bounded workspace and remove them after successful export.
- Preserve the original source and editable timeline while avoiding duplicate full-resolution intermediates.

The target working memory is `O(n)` for the active metadata and moment map, with media processed in streams or bounded chunks. Disk usage should grow mainly with source media, intentional proxies, cached assets, and final exports—not with repeated temporary copies.

Target complexity:

- Main processing: `O(n)`.
- Lookup: average `O(1)`.
- Ranking and sorting: `O(n log n)` where needed.
- Avoid `O(n²)` comparisons and exponential combinations.

## Build order

1. Document the existing short-form pipeline and preserve its behavior.
2. Add source inspection and raw-visual detection.
3. Add transcript moment mapping and football-context entities.
4. Add event-grounded asset search and source manifests.
5. Add the editable timeline and moment-level review controls.
6. Add source-preserving enhancement treatments.
7. Add stats, quotes, memes, screenshots, and muted reference clips.
8. Add long-form assembly and horizontal rendering.
9. Derive vertical cuts from the same timeline.
10. Add rights review, fallback instructions, caching, and QA.

The first milestone is a single pilot episode that proves the moment map, source-aware visual decisions, editable review, audio placement, and long-form-to-Shorts export.
