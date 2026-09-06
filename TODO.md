# Where Gab stands, and what is left

Written at the end of the first build session. Everything below the first
section is working, tested and pushed.

## STOP - do not share the installer yet

`gab/config.py` has `MICROPHONE = "HyperX Quadcast"`, and `audio.find_microphone()`
raises when nothing matches that name. On any other machine Gab dies during
startup, and because the packaged app has no console the person sees nothing
at all - no window, no error. The only trace is `%LOCALAPPDATA%\Gab\gab.log`.

A zip was built at `D:\Gab-for-testing.zip` (3.12 GB, installer plus a note for
a tester). **It has this bug in it. Do not send it.**

The real fix is the next item, not a patch to the default.

## 1. Settings that survive installation

Everything configurable lives in `config.py`, which PyInstaller freezes into
the exe. After installing, nobody can change the microphone, the model, the
wake word sensitivity or anything else.

Needs a settings file written on first run - somewhere writable such as
`%LOCALAPPDATA%\Gab\settings.toml` - that `config.py` reads and falls back to
sensible defaults for. Microphone should default to the system default device,
with a name only as an optional preference.

## 2. Doing things, not just answering

Opening apps, opening web pages, playing a song or a video. This was in the
original scope as "later", and the v1 plan said a stub would go in so the
architecture was ready. That stub was never built. `brain._route()` currently
answers with `direct`, `search` or `weather` only - adding verbs there is the
natural place for it.

## 3. The wake word

Still the stand-in `hey_jarvis`. "Hey Gab" needs training. The hosted trainer at
openwakeword.com charges credits; the free route is the project's own Colab
notebook, about an hour, mostly waiting:

https://colab.research.google.com/github/dscripka/openWakeWord/blob/main/notebooks/automatic_model_training.ipynb

Change one line - `config["target_phrase"] = ["hey gab"]` - set the runtime to a
T4 GPU, run all, download the .onnx, and point `config.WAKE_MODEL` at it.

Bare "Gab" on its own is a bad idea: one syllable, and it will fire on grab,
gap, cab and ordinary speech.

## 4. Knowing when you have stopped talking

A fixed 1.0 second timer. Measured against real speech, a natural mid-sentence
pause ran just under 0.8s, so this clears it by very little, and a slower
talker gets cut off. 1.5s was tried and felt sluggish.

The proper fix is voice-activity detection, which can tell a thinking pause
from a finished sentence and would be both safer and faster. Silero is already
on disk - openWakeWord bundles it at
`runtime/wakeword/` alongside the other models - so nothing new needs
downloading.

`tune_timing.py` records takes and `analyse_takes.py` replays them against
candidate settings without anyone having to speak again.

## 5. Smaller known problems

- The room is measured once at startup. A noise at that exact moment sets a bad
  threshold for the whole session. VAD also fixes this.
- Nothing interrupts an answer once it starts speaking.
- No conversation memory. Every question stands alone, so no follow-ups.
- When search results disagree it takes the most recent, which is not always
  the right one.

## 6. Voice, personality, animation

Wanted together, in roughly this order.

- **Voice.** The five Piper voices were all found wanting; `en_GB-cori-high` is
  a placeholder. Kokoro is the candidate - still local, still no account, much
  more natural, around 350 MB.
- **Personality.** Lives in `config.SYSTEM_PROMPT`. The catch: that prompt
  currently demands "one or two short sentences, no preamble", which is exactly
  what keeps answers fast and stops the model rambling. Personality needs room
  to breathe, so this is a tradeoff to tune rather than a line to add. Also
  worth testing whether a 4B model can hold a character over a whole answer.
- **Animations.** The orb already repaints at 60fps with a running clock, so
  there is no plumbing to add - it is design work. Today: appearing and
  disappearing is a 200ms opacity fade and nothing else, and the state colour
  is swapped in a single assignment so blue snaps to purple in one frame.
  Blending between palettes is likely the biggest single visual win.

## 7. Someday

Code signing, to stop the SmartScreen warning on the installer. A few hundred
dollars a year, so not a hobby-project decision.

## Things worth not forgetting

- The C: drive hit **zero bytes free** during the build. Cleaned up to ~3 GB,
  but that is still critical and most of it is not this project. Builds now
  write to `D:\GabBuild`.
- Qwen narrates its reasoning unless `--reasoning off` is passed. Left on, it
  spends its whole token budget thinking out loud and returns an empty answer.
  Check this if the model is ever swapped.
- Native tool calling was tried for search and abandoned - the 4B model
  volunteered a search only about half the time and would announce it needed to
  look something up without doing it. The separate one-line routing question
  gets 21 out of 21.
- The Vulkan build of llama.cpp is 35 MB against 254 MB plus a 391 MB runtime
  for the CUDA one, and works on AMD, Intel and NVIDIA alike.
