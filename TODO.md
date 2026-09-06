# Where Gab stands, and what is left

Written at the end of the first build session. Everything below the first
section is working, tested and pushed.

## DONE - the microphone blocker and the settings gap

Both fixed in 0.2.0.

`settings.json` now lives beside the log in `%LOCALAPPDATA%\Gab\`, holding the
microphone, the volume and the wake word sensitivity. `config.py` keeps the
defaults; the tray panel writes the file. The microphone defaults to the
system default and a chosen one is treated as a preference - if it is missing,
Gab says so in the log and uses the default rather than refusing to start.

**The old `D:\Gab-for-testing.zip` still contains the broken 0.1.0 build.
Delete it.** The 0.2.0 installer replaces it, and is small enough to put on
GitHub instead of sending as a file.

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

---

# Added after the first session

Ideas raised the same night, listed roughly in the order they would be built.
Most of them turn out to be one piece of work wearing several hats: the
settings file, the model picker and the tray panel all need the same thing -
somewhere outside the frozen exe to keep a choice, and somewhere to make it.

## 8. The tray panel

Clicking the tray icon opens a small panel. Asked for a volume slider, which
does not exist today at all - `voice.speak()` plays at whatever the system
volume is.

Worth putting in the same panel:

- **Microphone picker.** This is where the blocker at the top of this file
  gets properly fixed rather than patched.
- **Pause listening.** A toggle for calls, films, company. In an always-on
  app this ends up the most-used control, and today the only way to stop it
  is quitting.
- **Stop talking.** Cuts off an answer part way. The cheap version of the
  interrupt problem in section 5; real barge-in is much harder.
- **Wake word sensitivity.** One slider. Too many or too few triggers is the
  usual complaint, and the right number differs by room and microphone.
- The model picker from section 9.

Deliberately not included: conversation history. It would turn a quick panel
into an app, and it means storing what people said, which cuts against the
nothing-is-kept story.

## 9. Choosing and downloading models

A dropdown to pick a language model, with suggestions for low, medium and
high end machines plus a longer list to choose from.

Open question, worth deciding on purpose: **how much ships in the installer.**
The original rule was one installer, no downloads, no sign-ins. Three options:

- Bundle nothing, pick during setup. Installer drops to roughly 500 MB and
  becomes something you can actually send. But the download stops being
  optional, offline install disappears, and first run becomes the riskiest
  moment - a stalled download instead of a working assistant. Needs progress,
  resume and retry.
- Bundle everything, as now. 3.2 GB, painful to share.
- Bundle the smallest usable model and offer upgrades. Around 1-1.5 GB, still
  works the moment it installs, keeps the original promise.

The middle option looks best, but the case for the first got stronger the
moment this had to be handed to somebody.

## 10. The detail view

The panel expands to show what is actually going on.

- Model, voice, wake word and microphone in use.
- **Whether the graphics card is really being used, and which one.**
  llama.cpp quietly runs on the processor if Vulkan does not take, and there
  is currently no way to tell. "Why is it slow on my machine" is the question
  that will come up most, and this answers it at a glance.
- Timings from the last question. Already printed to the log; showing them
  lets the person feeling the slowness see where it went.
- What it last looked up, if anything. The privacy claim is that only a
  search query ever leaves the machine - showing the query is what makes that
  checkable instead of a promise.
- Version number, and a button to open the log folder.

The point of all this is bug reports. Yesterday a tester would have seen
nothing at all - no window, no error, no hint a log existed. One screenshot
of this panel gives the model, the microphone, the graphics card and the
timings.

## 11. System usage, and what to do about it

Show what the model is costing, so people can judge whether to size up or
down:

- Video memory used against available. The real constraint - a model either
  fits on the card or spills to system memory and crawls.
- Words per second. The best single signal: faster than speech means there is
  headroom.
- Memory and processor use, idle and while answering. The idle figure matters
  too - people want to know the cost of just listening.

Design note: raw numbers will not answer the question for most people.
"3.1 GB of 16 GB, 127 tokens a second" still leaves them guessing. Give a
verdict - *your card has room and answers arrive faster than speech, so a
larger model would run fine* - with the numbers underneath for anyone who
wants them.

Get the memory figures from llama.cpp itself rather than from Windows. It
reports what it loaded and where at startup, which works the same on AMD,
Intel and NVIDIA; asking the operating system differs per vendor.

## 12. Tidy the repository

The root is currently the app next to a heap of loose dev scripts.

Proposed shape:

- `gab/` - the app, already fine
- `tools/` - tune_timing, analyse_takes, compare_voices, debug_brain,
  render_preview, check_setup, the test scripts
- `packaging/` - gab.spec, installer.iss, make_share_zip.ps1
- `docs/` - this file, and the preview images out of the root

Three things that would do more for how the page looks than any folder move:

- **A screenshot or short GIF of the orb in the README.** Biggest single
  difference between a project and a folder. `render_preview.py` already
  makes the images.
- **A LICENSE file.** Not only cosmetic: openWakeWord and Piper are
  Apache-2.0 and llama.cpp is MIT, all fine, but **Qwen's model licence is
  worth actually reading** before the repo goes public or the installer goes
  to anyone beyond a friend.
- A description and topics on the repo, and making it public if people are
  meant to find it.

Note: the installer cannot be attached to a GitHub release. Their limit is
2 GB per file and it is 3.2 GB - another argument for shrinking what ships.

---

# Decided: how it gets to people

This settles the open question in item 9.

**The rule is that the user does nothing but run the installer.** It is not
that the machine never touches the internet. Those were being treated as the
same requirement and they are not.

So:

- **The installer downloads the model itself, during installation.** Not on
  first run - when the installer finishes, the app works. No prompt, no
  choice, no second step.
- **Everything comes from GitHub.** No Google Drive, no file services, no
  sending links around. Someone finds the repo, downloads one file, runs it.
- The model itself is fetched from wherever it lives, but the person never
  sees that or has to care.

What this changes:

- The installer drops to roughly 500 MB, which **fits under GitHub's 2 GB
  release limit** - the thing that made releases impossible yesterday.
- Offline installation goes away. Accepted deliberately.
- The model dropdown in item 9 stops being part of setup and becomes purely
  an optional upgrade later, in the tray panel.

What this now requires, and none of it is free:

- Inno Setup 6 can download during installation without any add-on, so the
  mechanism exists. It still needs a **progress display, a retry, and a
  message a normal person can act on** when the network drops halfway.
- **Verify what was downloaded.** A model file that arrives truncated will
  not announce itself - it will fail later in some confusing way. Check the
  size and hash before declaring success.
- Decide what a failed download leaves behind. Best is an installed app that
  says plainly what is missing and offers to try again, rather than an app
  that silently does not start - which is exactly the failure mode that bit
  us yesterday.
- A slow connection makes install take a long while. The progress display is
  what stops that reading as a hang.

---

# 13. The installer's looks

Seen during the first real install of 0.2.0. It works, but:

- **No time remaining and no speed.** "179 MB of 2777 MB" says nothing about
  whether that is five minutes or an hour, and on a slow connection that is
  exactly when someone decides it has frozen and kills it. Fix this first;
  it is the only item here that is not cosmetic. Track bytes against time in
  `OnDownloadProgress` and show something like "about 4 minutes left,
  11 MB/s".
- **No identity.** The title bar is Inno's default red, the corner shows a
  generic disc, and the app has no icon at all - `gab.spec` still has
  `icon=None`, so Gab.exe is a blank Windows default. Draw the orb as an .ico
  and use it for `SetupIconFile`, the wizard images and the exe.
- **Two thirds of the page is empty.** Inno sizes it for a full wizard while
  four lines are shown. The space could carry what is being installed and
  where it is going.
- **"Stop download" is the only button on screen**, which makes the one
  action nobody wants the most clickable thing in the window.

The ceiling is worth knowing: Inno's wizard is themeable but not deeply.
Icons, images, colours and page content are reachable; the shape of it is
not. Going further means a custom installer, which is a lot of work for
something people do once. Do the time remaining and the icon, then stop.
