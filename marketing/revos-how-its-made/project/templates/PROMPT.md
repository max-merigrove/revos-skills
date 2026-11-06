# {{TITLE}}: build prompt

The fixed look is `STYLE.md` sections 3 and 4 (dark product studio, warm key, cool rim,
slow camera, one shot per sentence; top captions with a blue keyword box, tracked
callouts, stats). Build with the kit in this repo (HyperFrames + Three.js);
in Remotion the same blocks map onto `@remotion/three` with `useCurrentFrame()`.

Spoken words: {{WORDS}} (about {{SECONDS}} s at 2.8 words a second).

## The one idea

{{ONE LINE: what the viewer knows at the end that they did not at the start}}

## Shots

<!-- One block per sentence. "world" is what is built in 3D; anything that must be a real
     photo or a generated picture goes in IMAGES.md and is named here as a plate. -->

```
SHOT 1  hook  (line: "...")
  length   on the voice, ~3 s, frame 0 already shows the object
  world    ...
  motion   ...
  camera   ...
  labels   ...
  caption  keyword "...", emoji ...
```

## Sound

Voice: {{Max records it | TTS voice name | scratch}}. Music bed: dark ambient, 12 % under the
voice. Small sounds on: {{the press, the hiss, the snap, each callout}}.
