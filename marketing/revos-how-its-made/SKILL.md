---
name: revos-how-its-made
description: >-
  Make a 60 to 90 second vertical "how it's made" explainer reel in the speedy_devv
  style (dark product-studio 3D, one step per sentence, top captions with a blue
  keyword box, callouts that track the parts, stats that count up): research the
  real process, write the spoken script, write the shot-by-shot build prompt and the
  list of pictures to source or generate, stop for Max's approval, then build it in
  HyperFrames + Three.js with the merigrove-how-its-made kit and render it. Includes a
  set-up checklist and installer for a new machine. Use when Max gives a topic like
  "how a pencil is made", "how are tyres made", "explain how X works as an animation",
  "make one of those how-it's-made reels", asks for the script or the animation prompt
  for one, or asks to set up or check the tools for these reels.
---

# How it's made

## The project

The project is wherever the set-up below put it (a folder named
`merigrove-how-its-made` on Max's machine): ask once, then remember the path. Every
command in this skill runs from the project folder.

Read its `STYLE.md` (the look, measured from the reference reels) and `README.md` (the
kit, `reel.json`, the traps) before step 3. The worked example is the pencil reel
(`reels/example_Pencil/` after set-up):
copy its patterns (`assets/shots.js`, `reel.json`).

Before rendering anything, load the `hyperframes` skill. Hooks go through `hook-method`.
The script goes through `ig-human` before Max sees it. British English throughout.

## Before the first reel: set-up checklist

Once per machine. If the project already exists, run `npm run doctor` in it: if it ends
"Ready.", skip this section. Otherwise work down the list; each box says how to check it
and how to fix it. The skill folder carries everything else (`project/` is the kit,
scripts, templates and docs; `examples/pencil/` is the worked example with its voice).

**Software (macOS commands; Homebrew from brew.sh if `brew` is missing)**

- [ ] **Node.js 22 or newer.** Check `node -v`. Fix `brew install node@22` (or `nvm install 22`).
- [ ] **ffmpeg and ffprobe 8 or newer** (renders, joining the voice, contact sheets).
      Check `ffmpeg -version`. Fix `brew install ffmpeg`.
- [ ] **HyperFrames CLI 0.9.9 and its render browser.** Check
      `npx --yes hyperframes@0.9.9 doctor`: "Chrome" ticked. Fix
      `npx hyperframes@0.9.9 browser ensure`. Docker, Kokoro and MusicGen in that list
      are optional and not used here.
- [ ] **Whisper** (word times for every caption and cut). Check: the same doctor shows
      "whisper-cpp" ticked. Fix `brew install whisper-cpp`, or let
      `npx hyperframes transcribe` install it on first use (the small.en model, about
      470 MB, downloads on the first transcription).
- [ ] **Python 3 with numpy and scipy** (the pronunciation check). Check
      `python3 -c "import numpy, scipy"`. Fix `python3 -m pip install --user numpy scipy`.
- [ ] **Emoji font** for caption emoji. macOS has Apple Color Emoji. Elsewhere install
      Noto Color Emoji and change the `@font-face` at the top of `kit/overlay.css`.
- [ ] **5 GB free disk.** A master render is about 400 MB; the phone copy about 45 MB.

**Skills (in `~/.claude/skills/`)**

- [ ] **hyperframes** and **hyperframes-cli** (required). Fix
      `npx hyperframes@0.9.9 skills`, then start a new Claude session so they load.
- [ ] **hook-method** and **ig-human** (optional, Max's own). Without them, judge hooks
      by `STYLE.md` section 2 and read the script aloud once for AI tells.

**The project**

- [ ] **Create it.** Ask where it should live, then:
      `node ~/.claude/skills/revos-how-its-made/project/scripts/setup.mjs "<folder>"`.
      This copies the kit, runs `npm install` (Three.js 0.170, esbuild) and
      `npm run vendor` (builds `kit/three.bundle.js`), adds `reels/example_Pencil/`,
      and runs the doctor. To refresh an existing project's kit from the skill:
      add `--update` (reels are left alone).
- [ ] **Doctor passes.** `npm run doctor` in the project ends "Ready." Its last check
      renders one 3D frame and measures it: "Test render (WebGL) ✓" means the GPU path
      works. If that one fails, look at the frame it names, then try
      `npx hyperframes snapshot --no-browser-gpu` to test software WebGL.

**Connectors and accounts (Claude checks these itself)**

- [ ] **Fish Audio** (only for a generated voice). Connected in claude.ai Settings →
      Connectors, and authorised: `get_credit_balance` answers. Note the plan: the free
      plan allows 500 bytes a call (the voice script splits for this) and about 1 credit
      a character, so a 60 s reel costs about 1,000 credits. Max's voice is Sarah
      (`933563129e564b19a115bedd57b7406a`).
- [ ] **Web search** works (step 2's research).

**First run**

- [ ] **Render the example** to see the target and time the machine:
      `cd reels/example_Pencil && npx hyperframes render -o Output/example.mp4 -f 30 -q high --browser-gpu`
      (about 2 to 5 minutes on an M-series Mac). Look at it before making a new reel.

**After changing the kit** (Max's machine): `npm run pack-skill` in the project copies
the kit, scripts, templates and the pencil example back into this skill, so the next
set-up gets the latest.

## The steps

Do them in order. Stop at step 6 for Max; do not build before he approves.

### 1. Start the reel

```bash
node scripts/new-reel.mjs "How a pencil is made"
```

Makes `reels/<date>_<Slug>/` with `script.txt`, `facts.md`, `PROMPT.md`, `IMAGES.md`,
`reel.json` and `assets/shots.js` from `templates/`.

### 2. Research the real process

Search the web (several searches in one turn) for how the thing is actually made:
the steps in order, the materials, and one concrete number per step (temperature,
pressure, size, count, time). Prefer manufacturers, trade bodies and encyclopaedias
over listicles. Write every claim the script will make into `facts.md` with its
source. A number with no source is cut or said as "about". Find the one surprising fact that turns the process into a story: the
misconception the hook will kill (tyre hairs are not for grip; there is no lead in a
pencil).

### 3. Write the script

`STYLE.md` section 2 is the shape. In short:

1. **Hook** (under 4 s): the question the viewer already has, or the myth said as
   fact. Write three, judge them with `hook-method`, keep the strongest.
2. **Snapback**: one line that kills the obvious answer.
3. **Process**: 5 to 9 sentences, one step each, in order, each with one number said
   the way people say it ("about a thousand degrees", "nine grooves").
4. **Analogy**: one kitchen object for the hardest step ("like spaghetti",
   "like toothpaste when you squeeze the tube").
5. **Payoff**: re-read the hook with what we now know.
6. **CTA**: "Follow, and send this to someone who still thinks ..." (the myth).

150 to 240 words (55 to 90 s at 2.8 words a second). Short sentences, second person.
Every sentence must be picturable: if a line has no object to show, rewrite it. Run
`ig-human` on it. Save to `script.txt`, one sentence per line, with a blank line between
sections (each section becomes one TTS call, so the joins fall where a narrator pauses).
Delivery tags go in the script where wanted: `[pause]` after the hook's first line and
before the payoff.

**Pronunciation pass.** Read every word of the script for heteronyms: words spelled one
way and said two ways. A voice guesses from grammar and often guesses wrong (the pencil's
first read said "leed" for the metal). Respell each one the way it is meant in
`reel.json` `pronounce` ({written: spoken}); the voice gets the respelling, the captions
keep the written word. Common in how-it's-made scripts:

| Word | Meaning here | Respell as |
| --- | --- | --- |
| lead | the metal, a pencil core | `led` |
| read | past tense | `red` |
| wind | to turn, coil | `wynd` |
| tear | to rip | `tair` |
| wound | coiled (past of wind) | `wownd` |
| close | near | `cloce` |
| minute | tiny | `my-newt` |
| live | alive, carrying current | `lyve` |
| row | an argument (rarely in these) | `rau` |
| bass | the fish | `bass` is fine; the low sound: `base` |
| produce, record, object, present, content, contract, conduct, project, permit, subject, refuse | noun vs verb (stress moves) | rewrite the sentence so the word is unambiguous, or keep the meaning the grammar makes obvious |

A respelling also changes what Whisper writes, but `build-reel.mjs` maps it back for the
captions. If the script also uses the respelled word for real ("she led"), rewrite one of them.

### 4. Write the build prompt (`PROMPT.md`)

One block per sentence, in the `STYLE.md` section 6 format: length, world, motion,
camera, labels, caption keyword (and emoji, under one in four lines).
Rules that make it look like the reference:

- One hero object per shot, lit in the dark studio; the object transforms during the
  shot (closes, squeezes, splits, glows) on the word that says so.
- Show the inside: cutaways, exploded views, X-ray, "magnified" slices.
- Consecutive steps on the same object dissolve (0.45 s); a new object cuts.
- Every number spoken is on screen as a stat or callout, on its word.
- Long objects lie along the depth axis or diagonally (the frame is 9:16).
- Frame 0 is the hook picture, never black.

### 5. List the pictures (`IMAGES.md`)

Anything the 3D should not draw: real people (a print on a desk, name above), historic
footage or places (sepia, with the year), a branded product, and analogy objects that
would be weak in primitives (a toothpaste tube, a finger in clay). Real people, places
and events are real photographs with a reusable licence, never generated. Generic
objects can be generated: write the prompt using the style suffix in the template.
Generation through the Fish Audio tools costs
credits: estimate first and ask Max before generating.

### 6. Stop for Max

Show him, in this order: the chosen hook with the two runners-up, `script.txt`, the
shot list from `PROMPT.md` as a short table (shot, line, what we see), and the
`IMAGES.md` table with what he needs to supply. Ask who voices it:

- **Max records it** (default): he sends a voice memo or WAV; save as `assets/vo.wav`.
- **TTS**: Fish Audio. Max's current voice is **Sarah** (`933563129e564b19a115bedd57b7406a`,
  model s2.1-pro) unless he says otherwise. About 1 credit per character; quote the
  total from step 7 and ask before generating.
- **Scratch**: `say -v Daniel -r 182 -f script.txt -o assets/vo.aiff`, then
  `ffmpeg -i assets/vo.aiff -ar 48000 -ac 1 assets/vo.wav`, for timing only; never
  the delivery voice.

Apply his notes, then build.

### 7. Build

A recorded voice: save it as `assets/vo.wav`. A TTS voice:

```bash
node scripts/voice.mjs text reels/<dir>     # applies pronounce, splits into parts under 500 bytes
```

Call `text_to_speech` once per part with the exact text it prints (all parts in one
turn), download each `audio_url` with `curl` to `assets/voice/part1.mp3`, `part2.mp3` ...
(the link can 404 for a few seconds: retry the download, never regenerate, which charges
again), then:

```bash
node scripts/voice.mjs join reels/<dir>     # trims, 0.4 s breaths, -16 LUFS -> assets/vo.wav
cd reels/<dir>
npx hyperframes transcribe assets/vo.wav --model small.en
python3 ../../scripts/check-vowel.py . lead e   # for each lead/read heteronym: e = "led", ee = "leed"
node ../../scripts/build-reel.mjs .
```

Whisper's spelling is no proof of pronunciation (it writes "lead" from context either
way); `check-vowel.py` measures the vowel itself. For other heteronyms, cut the word out
(`ffmpeg -ss <start> -t <len>`) and listen, or transcribe it alone with no context.

- Read the transcript first: fix misheard words in `captions.fix` (US spellings too:
  "gray" to "grey"). Whisper writes numbers as digits on one take and words on the next,
  so anchor numbers with both: `"at": "1000|thousand"`.
- `reel.json`: one shot per sentence, each `at` its first spoken word (pick a word that
  only occurs there; "a" and "the" match the wrong place), `marks` for every move inside
  a shot, callouts and stats on the words that name them, `highlight` one keyword per
  sentence in order.
- `assets/shots.js`: one `HM.shot` per shot, from the `PROMPT.md` blocks. Reuse the
  pencil's builders as patterns (instanced particles for powders and atoms, clipping
  planes for cutters, a hero group that spins about its own length, `lump()` for
  organic shapes). Keep every move a function of `local` and the marks.
- Re-run `build-reel.mjs` after every change to `reel.json` or the voice.

### 8. Look, fix, look again

```bash
npx hyperframes check --json        # fix every error
npx hyperframes snapshot --at <one time per shot, mid-shot> --no-end --timeout 120000
```

Read the contact sheet and check each frame against this list before showing Max:

- The object fills 50 to 80 % of the width, centred, nothing important under y 168 px
  or over y 1330 px, nothing cut by the frame edge that should not be.
- No blown-out white areas (paper, emissive heat, bloom); heat reads orange-red.
- No floor horizon line; the background falls to near-black.
- Callouts sit on their part, inside the frame, clear of the caption.
- The caption line is centred and never ends on "a", "the", "like".
- Each shot visibly changes (something moves on its words).

Snapshot again after fixing. The README "Traps" section lists the fixes already found.

### 9. Render and deliver

```bash
npx hyperframes render -o Output/<Slug>.mp4 -f 30 -q high --browser-gpu
```

Run it in the background (about a minute of render per 10 s of film on this Mac). Make a
contact sheet of the render (one frame every 2 s) and look at it before telling Max it is
done. Send him the MP4 and say what is scratch (voice, missing pictures).

## Remotion instead

The `PROMPT.md` blocks are engine-neutral. In Remotion: one `<ThreeCanvas>` per shot
(`@remotion/three`), time from `useCurrentFrame() / fps`, captions as a React layer;
keep the same STYLE.md numbers. The kit in this repo is HyperFrames only.
